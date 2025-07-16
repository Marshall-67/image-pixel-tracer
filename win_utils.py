import win32api
import win32con
import win32gui
import time
import ctypes
from config import KEY_POLL_INTERVAL, CALIBRATION_SLEEP, MIN_ALPHA, MAX_ALPHA, HOTKEY_METHOD_MAP
 
def set_clickthrough(hwnd, alpha, enabled):
    """Toggles the click-through property of a window using pywin32."""
    try:
        # Clamp alpha to safe range
        alpha = max(MIN_ALPHA, min(MAX_ALPHA, alpha))
        styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        styles |= win32con.WS_EX_LAYERED  # Always set layered

        if enabled:
            styles |= win32con.WS_EX_TRANSPARENT
        else:
            styles &= ~win32con.WS_EX_TRANSPARENT

        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, styles)
        # Convert alpha to 0-255, clamp to at least 26 (0.1*255)
        win32_alpha = max(26, min(255, int(alpha * 255)))
        win32gui.SetLayeredWindowAttributes(hwnd, 0, win32_alpha, win32con.LWA_ALPHA)
    except Exception as e:
        print(f"Error setting clickthrough/alpha: {e}")

def get_vk_code(key_str):
    """Converts a key string (like 'Insert', 'A') to a virtual key code."""
    if not key_str:
        return None
    key_str = key_str.upper()
    if hasattr(win32con, f'VK_{key_str}'):
        return getattr(win32con, f'VK_{key_str}')
    return win32api.VkKeyScan(key_str.upper())

def poll_global_keys(app_instance):
    """
    Polls for global key presses using GetAsyncKeyState in a background thread.
    Uses dynamic hotkey polling based on the app_instance's hotkey_map.
    """
    key_states = {}
 
    def is_key_pressed(vk_code):
        state = ctypes.windll.user32.GetAsyncKeyState(vk_code)
        is_down = state & 0x8000
        if is_down and not key_states.get(vk_code):
            key_states[vk_code] = True
            return True
        elif not is_down:
            key_states[vk_code] = False
        return False

    while not app_instance.stop_polling:
        # Check if we're calibrating - if so, skip global key handling
        if hasattr(app_instance, 'is_calibrating') and app_instance.is_calibrating:
            time.sleep(CALIBRATION_SLEEP) # Sleep to avoid busy-waiting
            continue

        # Check for Ctrl modifier state
        is_ctrl_down = win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000

        # Dynamic hotkey polling - iterate through hotkey_map
        for action, key_str in app_instance.hotkey_map.items():
            # Handle special cases for Ctrl+ combinations
            if key_str.startswith('Ctrl+'):
                if not is_ctrl_down:
                    continue
                key_str = key_str[5:]  # Remove 'Ctrl+' prefix
            
            vk_code = get_vk_code(key_str)
            if vk_code and is_key_pressed(vk_code):
                # Get the corresponding method name
                method_name = HOTKEY_METHOD_MAP.get(action)
                if method_name:
                    method_to_call = getattr(app_instance, method_name, None)
                    if method_to_call:
                        app_instance.root.after_idle(method_to_call)
 
        time.sleep(KEY_POLL_INTERVAL)