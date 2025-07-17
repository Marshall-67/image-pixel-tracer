# Image processing configuration
CHUNK_SIZE = 32

# Display defaults
DEFAULT_ALPHA = 0.7
DEFAULT_SCALE = 1.0
CALIBRATED_SCALE = 15.0
MIN_SCALE = 0.1
MAX_SCALE = 15.0
MIN_ALPHA = 0.1
MAX_ALPHA = 1.0

# Visual styling
GRID_COLOR_FULL = "#777777"
GRID_COLOR_PIXEL = "#444444"
HIGHLIGHT_COLOR = "#ff3333"
TRANSPARENT_COLOR = 'lime'
SUCCESS_COLOR = "green"

# Window positioning
DEFAULT_WINDOW_X = 200
DEFAULT_WINDOW_Y = 200

# Hotkey configuration
DEFAULT_HOTKEYS = {
    'toggle_visibility': 'Insert',
    'next_chunk': 'Right',
    'prev_chunk': 'Left',
    'increase_opacity': 'Add',
    'decrease_opacity': 'Subtract',
    'increase_scale': 'Ctrl+Add',
    'decrease_scale': 'Ctrl+Subtract',
    'reset_scale': 'R',
    'toggle_single_chunk': 'S',
    'toggle_clickthrough': 'C',
    'stop_drawing': 'F12',
}

# Method mapping for hotkey actions
HOTKEY_METHOD_MAP = {
    'toggle_visibility': 'toggle_image_window_visibility',
    'next_chunk': 'next_chunk',
    'prev_chunk': 'prev_chunk',
    'increase_opacity': 'increase_opacity',
    'decrease_opacity': 'decrease_opacity',
    'increase_scale': 'increase_scale',
    'decrease_scale': 'decrease_scale',
    'reset_scale': 'reset_scale',
    'toggle_single_chunk': 'toggle_single_chunk_mode',
    'toggle_clickthrough': 'toggle_clickthrough_mode',
    'stop_drawing': 'stop_automated_drawing',
}

# Calibration settings
ZOOM_FACTOR = 8
ZOOM_AREA_SIZE = 32
ZOOM_DISPLAY_SIZE = ZOOM_AREA_SIZE * ZOOM_FACTOR

# Threading and polling
KEY_POLL_INTERVAL = 0.02
CALIBRATION_SLEEP = 0.05
SCREENSHOT_DELAY = 0.2 