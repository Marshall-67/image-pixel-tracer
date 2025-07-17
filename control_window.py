import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, NORMAL, DISABLED, HORIZONTAL, W, X, BOTTOM, Y
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageGrab
import os
import json
import threading
import time


from config import (
    CHUNK_SIZE, DEFAULT_ALPHA, DEFAULT_SCALE, CALIBRATED_SCALE,
    HIGHLIGHT_COLOR, DEFAULT_HOTKEYS, MIN_ALPHA, MAX_ALPHA,
    MIN_SCALE, MAX_SCALE
)
from image_window import ImageWindow
from win_utils import poll_global_keys
from calibration_window import CalibrationWindow
from color_assistant_window import ColorAssistantWindow
from image_utils import colors_are_similar
import pyautogui

class ControlWindow(ttk.Window):
    """
    The main GUI window with controls for the overlay.
    This window creates and manages the ImageWindow.
    """
    def __init__(self, original_image_path=None):
        super().__init__(themename="darkly")
        self.title("Dither-it Control @ Bob&Bill Inc")
        self.geometry("450x650+100+100")

        self.original_image_path = original_image_path
        self.chunk_folder = None
        self.original_pil_image = None
        self.image_window: ImageWindow | None = None
        self.is_calibrating = False
        self.hotkey_map = DEFAULT_HOTKEYS.copy()
        self.stop_polling = False
        self.is_drawing = False
        self.calibration_rect = None
        self.settings = {} # Add a settings dictionary
 
        self._load_settings() # Load settings on startup
        self.create_widgets()
        self._load_calibration_data()
 
        if self.original_image_path:
            self.load_image(self.original_image_path)

        self.key_poll_thread = threading.Thread(target=poll_global_keys, args=(self,), daemon=True)
        self.key_poll_thread.start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def get_total_chunks(self):
        if not self.chunk_folder:
            return 0
        from image_utils import count_existing_chunks
        return count_existing_chunks(self.chunk_folder) or (self.num_chunks_x * self.num_chunks_y)

    def create_widgets(self):
        """Creates all the control widgets in the main window."""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH)

        # --- Chunk Navigation ---
        chunk_frame = ttk.Labelframe(main_frame, text="Chunk Navigation", padding=10)
        chunk_frame.pack(fill=X, pady=(0, 10))
        
        self.chunk_slider = ttk.Scale(chunk_frame, from_=0, to=1, orient=HORIZONTAL, command=self.on_chunk_change)
        self.chunk_slider.pack(fill=X, pady=5)
        self.chunk_slider.config(state=DISABLED)
        
        self.chunk_label = ttk.Label(chunk_frame, text="Chunk: -/-")
        self.chunk_label.pack()

        # --- Display Controls ---
        display_frame = ttk.Labelframe(main_frame, text="Display Controls", padding=10)
        display_frame.pack(fill=X, pady=10)

        # Opacity Slider
        ttk.Label(display_frame, text="Opacity").pack(anchor=W)
        self.opacity_slider = ttk.Scale(display_frame, from_=0.1, to=1.0, value=DEFAULT_ALPHA, orient=HORIZONTAL, command=self.on_opacity_change)
        self.opacity_slider.pack(fill=X, pady=(0, 10))
        self.opacity_slider.config(state=DISABLED)

        # Scale Slider
        ttk.Label(display_frame, text="Scale").pack(anchor=W)
        self.scale_slider = ttk.Scale(display_frame, from_=0.1, to=15.0, value=DEFAULT_SCALE, orient=HORIZONTAL, command=self.on_scale_change)
        self.scale_slider.pack(fill=X, pady=(0, 10))
        self.scale_slider.config(state=DISABLED)

        # --- Mode Toggles ---
        mode_frame = ttk.Frame(main_frame)
        mode_frame.pack(fill=X, pady=10)
        
        self.single_chunk_var = tk.BooleanVar()
        self.single_chunk_toggle = ttk.Checkbutton(mode_frame, text="Single Chunk Mode", variable=self.single_chunk_var, command=self.on_toggle_single_chunk)
        self.single_chunk_toggle.pack(side=LEFT, expand=True)

        self.calibrate_button = ttk.Button(mode_frame, text="Calibrate", command=self.calibrate_single_chunk, state=DISABLED)
        self.calibrate_button.pack(side=LEFT, padx=5)

        self.load_button = ttk.Button(mode_frame, text="Load Image", command=self.load_image_from_dialog, state=NORMAL)
        self.load_button.pack(side=LEFT, padx=5)

        self.color_assistant_button = ttk.Button(mode_frame, text="Color Assistant", command=self.open_color_assistant, state=DISABLED)
        self.color_assistant_button.pack(side=LEFT, padx=5)

        self.clickthrough_var = tk.BooleanVar()
        self.clickthrough_toggle = ttk.Checkbutton(mode_frame, text="Click-Through", variable=self.clickthrough_var, command=self.on_toggle_clickthrough)
        self.clickthrough_toggle.pack(side=RIGHT, expand=True)
 
        # --- Stop Button ---
        self.stop_drawing_button = ttk.Button(
            main_frame,
            text="Stop Drawing",
            command=self.stop_automated_drawing,
        )
        # Initially hidden, shown only during drawing
        self.stop_drawing_button.pack(pady=5, fill=X)
        self.stop_drawing_button.pack_forget()

        # --- Progress Bar ---
        self.progress_bar = ttk.Progressbar(
            main_frame,
            orient=HORIZONTAL,
            length=100,
            mode='determinate'
        )
        self.progress_bar.pack(pady=5, fill=X)
        self.progress_bar.pack_forget()

        # --- Rebind Key ---
        rebind_frame = ttk.Frame(main_frame)
        rebind_frame.pack(fill=X, pady=5)
        self.rebind_button = ttk.Button(rebind_frame, text="Rebind Toggle Key", command=self.start_rebinding_toggle_key)
        self.rebind_button.pack()
        # --- Image Preview ---
        preview_frame = ttk.Labelframe(main_frame, text="Image Preview", padding=10)
        preview_frame.pack(fill=X, pady=5)

        self.preview_canvas = tk.Canvas(preview_frame, bg=self.cget('bg'), highlightthickness=0, height=100)
        self.preview_canvas.pack(fill=X, expand=False)
        self.preview_canvas.bind("<Configure>", self.draw_preview)

       # --- Info/Hotkeys ---
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(side=BOTTOM, fill=X, pady=(5,0))
        self.info_label = ttk.Label(info_frame, text="", justify=LEFT, font=("Segoe UI", 8))
        self.info_label.pack(anchor=W)
        self.update_hotkey_info()

    def update_hotkey_info(self):
        info_text = (
            "Hotkeys:\n"
            "  ↑↓: Next/Prev Chunk\n"
            "  Ctrl +/-: Zoom\n"
            "  +/-: Opacity\n"
            "  R: Reset Scale\n"
            "  C: Click-Through\n"
            "  S: Single Chunk\n"
            f"  {self.hotkey_map['toggle_visibility']}: Toggle Overlay"
        )
        self.info_label.config(text=info_text)

    def _load_settings(self):
        """Loads drawing settings from a JSON file."""
        try:
            with open('settings.json', 'r') as f:
                self.settings = json.load(f)
            print("Drawing settings loaded successfully.")
        except (FileNotFoundError, json.JSONDecodeError):
            print("Settings file not found or invalid. Using defaults.")
            # Define default settings here
            self.settings = {
                'drawing_speed': 0.05,
                'color_tolerance': 10,
                'double_click': False,
                'automated_mode': False,
                'grouping_sensitivity': 10.0
            }

    def _save_settings(self):
        """Saves the current drawing settings to a JSON file."""
        try:
            with open('settings.json', 'w') as f:
                json.dump(self.settings, f, indent=4)
            print("Drawing settings saved successfully.")
        except IOError as e:
            print(f"Error saving settings: {e}")

    def _load_calibration_data(self):
        """Loads calibration data from the JSON file."""
        try:
            with open('calibration.json', 'r') as f:
                data = json.load(f)
                self.calibration_rect = tuple(data['calibration_rect'])
                print("Calibration data loaded successfully.")
        except FileNotFoundError:
            print("Calibration file not found. Please calibrate.")
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading calibration data: {e}")

    def on_chunk_change(self, value):
        """Callback for when the chunk slider is moved."""
        if not self.image_window:
            return
        chunk_index = int(float(value))
        self.image_window.set_chunk(chunk_index)
        self.chunk_label.config(text=f"Chunk: {chunk_index + 1}/{self.total_chunks}")
        self.draw_preview()
        
    def on_opacity_change(self, value):
        """Callback for when the opacity slider is moved."""
        if not self.image_window:
            return
        self.image_window.set_alpha(float(value))

    def on_scale_change(self, value):
        """Callback for when the scale slider is moved."""
        if not self.image_window:
            return
        self.image_window.set_scale(float(value))
        if self.image_window.single_chunk_mode:
            self.scale_slider.set(15.0)

    def on_toggle_single_chunk(self):
        """Callback for single chunk mode toggle."""
        if not self.image_window:
            self.single_chunk_var.set(False) # Ensure var is in a predictable state
            return
        enabled = self.single_chunk_var.get()
        self.image_window.toggle_single_chunk(enabled)
        self.scale_slider.config(state=DISABLED if enabled else NORMAL)
        if enabled:
            self.calibrate_button.config(state=NORMAL if not self.calibration_rect else DISABLED)
            self.scale_slider.set(CALIBRATED_SCALE)
        else:
            self.calibrate_button.config(state=DISABLED)

    def on_toggle_clickthrough(self):
        """Callback for click-through mode toggle."""
        if not self.image_window:
            self.clickthrough_var.set(False) # Ensure var is in a predictable state
            return
        self.image_window.toggle_clickthrough(self.clickthrough_var.get())

    def open_color_assistant(self):
        """
        Opens the color assistant window, now passing the image path to it
        so it can perform its own color extraction.
        """
        if not self.original_image_path:
            messagebox.showerror("Error", "Please load an image before opening the Color Assistant.")
            return

        try:
            # Pass the loaded settings to the assistant
            assistant = ColorAssistantWindow(self, self.original_image_path, self.settings)
            self.wait_window(assistant)
            
            # --- After the assistant closes, update our settings dictionary ---
            if assistant.was_confirmed: # We'll add this flag to the assistant
                self.settings['drawing_speed'] = assistant.drawing_speed.get()
                self.settings['color_tolerance'] = assistant.color_tolerance.get()
                self.settings['double_click'] = assistant.double_click.get()
                self.settings['automated_mode'] = assistant.automated_mode.get()
                self.settings['grouping_sensitivity'] = assistant.grouping_sensitivity.get()

                if assistant.selected_colors and self.image_window:
                    # The drawing logic remains here
                    target_color = assistant.selected_colors[0]
                
                    if assistant.automated_mode.get():
                        self.start_automated_drawing(
                            target_color,
                            assistant.selected_colors,  # Pass the whole list
                            assistant.drawing_speed.get(),
                            assistant.color_tolerance.get(),  # This is the "matching" tolerance
                            assistant.double_click.get()
                        )
                    else:
                        # If not in automated mode, just highlight all selected colors
                        self.image_window.highlight_colors(
                            assistant.selected_colors,
                            assistant.color_tolerance.get() # Use the same tolerance for highlighting
                        )

        except Exception as e:
            # This is a fallback for errors during window creation
            messagebox.showerror("Error", f"Could not open Color Assistant: {e}")

    def start_automated_drawing(self, primary_color, all_colors, speed, tolerance, double_click):
        if not self.image_window or not self.image_window.single_chunk_mode:
            messagebox.showwarning("Mode Error", "Automated drawing requires Single Chunk Mode.")
            return

        if self.is_drawing:
            messagebox.showwarning("Busy", "Already drawing.")
            return

        self.is_drawing = True
        self.color_assistant_button.config(state=DISABLED)
        self.image_window.highlight_colors(all_colors, tolerance)
        self.stop_drawing_button.pack(pady=5, fill=X)
        self.progress_bar.pack(pady=5, fill=X)
        
        # Enable click-through
        self.clickthrough_var.set(True)
        self.on_toggle_clickthrough()

        # This should run in a separate thread to avoid freezing the GUI
        threading.Thread(target=self._drawing_thread, args=(primary_color, all_colors, speed, tolerance, double_click), daemon=True).start()

    def _drawing_thread(self, primary_color, all_colors, speed, tolerance, double_click):
        
        def _finish_drawing():
            """Called on the main thread to clean up the GUI after drawing."""
            if self.image_window:
                self.image_window.clear_color_highlight()
                self.image_window.clear_success_markers()
            
            if self.progress_bar.winfo_exists():
                # Fill the progress bar to show completion, then hide
                self.progress_bar['value'] = self.progress_bar['maximum']
                self.update_idletasks()
                time.sleep(0.2)
                self.progress_bar.pack_forget()

            self.is_drawing = False
            if self.color_assistant_button.winfo_exists():
                self.color_assistant_button.config(state=NORMAL)
            if self.stop_drawing_button.winfo_exists():
                self.stop_drawing_button.pack_forget()
            
            self.clickthrough_var.set(False)
            self.on_toggle_clickthrough()
            print("Automated drawing finished.")

        try:
            pyautogui.PAUSE = 0
            pyautogui.MINIMUM_DURATION = 0

            if not self.image_window or not (self.image_window.target_x is not None and self.image_window.target_w is not None):
                messagebox.showerror("Not Calibrated", "Please calibrate the drawing area first.")
                self.after(0, _finish_drawing)
                return

            # --- 1. Get initial ORDERED list of pixels to draw ---
            # DO NOT CONVERT TO A SET. Keep it as a list to preserve order.
            pixels_to_try = self.image_window.get_pixel_locations_for_colors(all_colors)
            if not pixels_to_try:
                print("No pixels of the specified color found.")
                self.after(0, _finish_drawing)
                return

            # --- 2. Setup for retries and progress tracking ---
            retry_counts = {loc: 0 for loc in pixels_to_try}
            MAX_RETRIES = 3
            total_pixels = len(pixels_to_try)
            completed_count = 0
            
            self.after(0, lambda: self.progress_bar.config(maximum=total_pixels, value=0))
            
            original_pos = pyautogui.position()

            # --- 3. The new ORDERED drawing loop ---
            while pixels_to_try and self.is_drawing:
                failed_this_pass = []
                
                # Iterate through the current list of pixels to try this pass
                for pixel_location in pixels_to_try:
                    if not self.is_drawing:
                        break # Exit inner loop if user stopped
                    
                    (screen_x, screen_y) = pixel_location

                    # A. --- MODIFIED DRAWING ACTION ---
                    # Replace the simple click with a more robust, tiny drag.
                    
                    # Move to the target pixel first.
                    pyautogui.moveTo(screen_x, screen_y)
                    
                    if double_click:
                        # Perform a standard click first (to select the tool/color)
                        pyautogui.click()
                        # Then perform the tiny drag to apply the color
                        pyautogui.dragRel(0, 1, duration=0.05, button='left')
                    else:
                        # Just perform the tiny drag. This holds the left button,
                        # moves 1 pixel down, and releases.
                        pyautogui.dragRel(0, 1, duration=0.05, button='left')

                    # The user-defined speed delay is still respected after the action
                    if speed > 0:
                        time.sleep(speed)

                    # B. Verify the click
                    try:
                        pixel_img = ImageGrab.grab(bbox=(screen_x, screen_y, screen_x + 1, screen_y + 1))
                        current_pixel_color = pixel_img.getpixel((0, 0))
                        is_successfully_drawn = any(colors_are_similar(current_pixel_color, c, tolerance) for c in all_colors)
                    except Exception as e:
                        print(f"Could not verify pixel at ({screen_x}, {screen_y}): {e}")
                        is_successfully_drawn = False # Treat verification error as a failure

                    # C. Handle success or failure
                    if is_successfully_drawn:
                        # Success! Mark it and increment completion count.
                        if self.image_window:
                            self.image_window.mark_pixel_as_successful(screen_x, screen_y)
                        completed_count += 1
                    else:
                        # Failure! Check retry count.
                        retry_counts[pixel_location] += 1
                        if retry_counts[pixel_location] < MAX_RETRIES:
                            failed_this_pass.append(pixel_location) # Re-queue for the next pass
                        else:
                            # Gave up on this pixel, but it's "complete" for progress purposes
                            print(f"Pixel at {pixel_location} failed to draw after {MAX_RETRIES} attempts. Skipping.")
                            completed_count += 1
                    
                    # Update progress bar after every attempt
                    self.after(0, lambda p=completed_count: self.progress_bar.config(value=p))

                if not self.is_drawing:
                    break # Exit outer loop if user stopped

                # Prepare for the next pass with only the pixels that failed
                pixels_to_try = failed_this_pass

            pyautogui.moveTo(original_pos)

        except Exception as e:
            print(f"An error occurred during automated drawing: {e}")
        finally:
            pyautogui.PAUSE = 0.1
            self.after(0, _finish_drawing)

    def stop_automated_drawing(self):
        """Stops the drawing process."""
        self.is_drawing = False

    def calibrate_single_chunk(self):
        """
        Launch a modal, fullscreen calibration window.
        """
        if not self.single_chunk_var.get() or not self.image_window:
            return

        self.is_calibrating = True
        
        try:
            # Create and show the calibration window
            selector = CalibrationWindow(self)
            self.wait_window(selector)  # Wait until the window is destroyed
            
            # Apply calibration if result was obtained
            if selector.result and self.image_window:
                self.calibration_rect = selector.result
                x_min, y_min, width, height = self.calibration_rect
                self.image_window.set_calibration(x_min, y_min, width, height)
                
        finally:
            self.is_calibrating = False


    def draw_preview(self, event=None):
        """Draws the preview image and chunk highlight on its canvas."""
        if not self.original_pil_image:  # Don't draw if no image is loaded
            return
            
        canvas_w = self.preview_canvas.winfo_width()
        canvas_h = self.preview_canvas.winfo_height()
        if canvas_w < 20 or canvas_h < 20:  # Don't draw if canvas is too small
            return

        self.preview_canvas.delete("all")
        
        # Calculate scale to fit image in canvas
        img_w, img_h = self.original_pil_image.size
        scale = min(canvas_w / img_w, canvas_h / img_h)
        preview_w, preview_h = int(img_w * scale), int(img_h * scale)

        # Create and display preview image
        preview_img = self.original_pil_image.resize((preview_w, preview_h), Image.Resampling.LANCZOS)
        # Use a different attribute name to avoid conflicts
        self.preview_tk_image_ref = ImageTk.PhotoImage(preview_img)
        self.preview_canvas.create_image(canvas_w / 2, canvas_h / 2, image=self.preview_tk_image_ref, anchor='center')

        # Draw highlight on the current chunk
        chunk_index = int(self.chunk_slider.get())
        row = chunk_index // self.num_chunks_x
        col = chunk_index % self.num_chunks_x
        
        chunk_w_preview = scale * CHUNK_SIZE
        chunk_h_preview = scale * CHUNK_SIZE
        
        # Calculate top-left corner of the preview image on the canvas
        offset_x = (canvas_w - preview_w) / 2
        offset_y = (canvas_h - preview_h) / 2

        x1 = offset_x + col * chunk_w_preview
        y1 = offset_y + row * chunk_h_preview
        x2 = x1 + chunk_w_preview
        y2 = y1 + chunk_h_preview

        self.preview_canvas.create_rectangle(x1, y1, x2, y2, outline=HIGHLIGHT_COLOR, width=2)

    def load_image(self, image_path):
        """Loads and processes the image from the given path."""
        self.original_image_path = image_path
        self.original_pil_image = Image.open(self.original_image_path)

        # --- Create output folder ---
        base_name = os.path.splitext(os.path.basename(self.original_image_path))[0]
        self.chunk_folder = os.path.join("output", base_name)
        os.makedirs(self.chunk_folder, exist_ok=True)

        # --- Split image into chunks ---
        from image_utils import split_image_into_chunks
        self.num_chunks_x, self.num_chunks_y, self.total_chunks = split_image_into_chunks(
            self.original_image_path, self.chunk_folder
        )

        # --- Update GUI ---
        self.title(f"Dither-it Control - {os.path.basename(self.original_image_path)}")
        self.chunk_slider.config(to=self.total_chunks - 1, state=NORMAL)
        self.opacity_slider.config(state=NORMAL)
        self.scale_slider.config(state=NORMAL)
        self.chunk_label.config(text=f"Chunk: 1/{self.total_chunks}")
        self.calibrate_button.config(state=DISABLED)
        self.color_assistant_button.config(state=NORMAL)

        # --- Create ImageWindow ---
        if self.image_window:
            self.image_window.destroy()
        self.image_window = ImageWindow(self, self.original_pil_image, self.num_chunks_x, self.num_chunks_y)
        if self.calibration_rect:
            x_min, y_min, width, height = self.calibration_rect
            self.image_window.set_calibration(x_min, y_min, width, height)
        
        self.chunk_slider.config(to=self.total_chunks - 1, state=NORMAL)
        self.chunk_slider.set(0)
        self.on_chunk_change(0)
        self.draw_preview()

        self.opacity_slider.config(state=NORMAL)
        self.scale_slider.config(state=NORMAL)



    def load_image_from_dialog(self):
        """Opens a file dialog to select an image and loads it."""
        filepath = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=([("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]),
        )
        if not filepath:
            return

        self.load_image(filepath)
    # --- Methods for global key polling ---
    def next_chunk(self):
        current_index = int(self.chunk_slider.get())
        next_index = (current_index + 1) % self.total_chunks
        self.chunk_slider.set(next_index)
        self.on_chunk_change(next_index)

    def prev_chunk(self):
        current_index = int(self.chunk_slider.get())
        prev_index = (current_index - 1 + self.total_chunks) % self.total_chunks
        self.chunk_slider.set(prev_index)
        self.on_chunk_change(prev_index)

    def increase_opacity(self):
        current_value = self.opacity_slider.get()
        new_value = min(MAX_ALPHA, round(current_value + 0.1, 2))
        self.opacity_slider.set(new_value)
        self.on_opacity_change(new_value)

    def decrease_opacity(self):
        current_value = self.opacity_slider.get()
        new_value = max(MIN_ALPHA, round(current_value - 0.1, 2))
        self.opacity_slider.set(new_value)
        self.on_opacity_change(new_value)

    def increase_scale(self):
        if self.image_window and not self.image_window.single_chunk_mode:
            current_value = self.scale_slider.get()
            new_value = min(MAX_SCALE, current_value + 0.1)
            self.scale_slider.set(new_value)
            self.on_scale_change(new_value)

    def decrease_scale(self):
        if self.image_window and not self.image_window.single_chunk_mode:
            current_value = self.scale_slider.get()
            new_value = max(MIN_SCALE, current_value - 0.1)
            self.scale_slider.set(new_value)
            self.on_scale_change(new_value)
            
    def reset_scale(self):
        if self.image_window and not self.image_window.single_chunk_mode:
            self.scale_slider.set(DEFAULT_SCALE)
            self.on_scale_change(DEFAULT_SCALE)

    def toggle_clickthrough_mode(self):
        self.clickthrough_var.set(not self.clickthrough_var.get())
        self.on_toggle_clickthrough()
        
    def toggle_single_chunk_mode(self):
        self.single_chunk_var.set(not self.single_chunk_var.get())
        self.on_toggle_single_chunk()
        
    def toggle_visibility(self):
        """Toggles the visibility of the ImageWindow."""
        self.toggle_image_window_visibility()

    def toggle_image_window_visibility(self, event=None):
        """Toggles the visibility of the ImageWindow."""
        if self.image_window:
            self.image_window.toggle_visibility()

    def start_rebinding_toggle_key(self):
        self.rebind_button.config(text="Press a key...", state=DISABLED)
        self.bind("<KeyPress>", self.on_key_press_rebind)

    def on_key_press_rebind(self, event):
        self.unbind("<KeyPress>")
        new_key = event.keysym.capitalize()
        self.hotkey_map['toggle_visibility'] = new_key
        self.update_hotkey_info()
        self.rebind_button.config(text="Rebind Toggle Key", state=NORMAL)
        
    def on_close(self):
        """Handle the window closing event."""
        self._save_settings() # Save settings before closing
        print("Closing application...")
        self.stop_polling = True
        self.key_poll_thread.join(timeout=1) # Wait for poll thread to finish
        if self.image_window:
            self.image_window.clear_cache()  # Clear cache before destroying
            self.image_window.destroy()
        self.destroy()

    @property
    def root(self):
        return self