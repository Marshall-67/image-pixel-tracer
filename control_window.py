import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, NORMAL, DISABLED, HORIZONTAL, W, X, BOTTOM, Y
from tkinter import filedialog
from PIL import Image, ImageTk
import os
import threading


from config import (
    CHUNK_SIZE, DEFAULT_ALPHA, DEFAULT_SCALE, CALIBRATED_SCALE,
    HIGHLIGHT_COLOR, DEFAULT_HOTKEYS, MIN_ALPHA, MAX_ALPHA,
    MIN_SCALE, MAX_SCALE
)
from image_window import ImageWindow
from win_utils import poll_global_keys
from calibration_window import CalibrationWindow
from image_utils import split_image_into_chunks, count_existing_chunks

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
        self.image_window = None
        self.is_calibrating = False
        self.hotkey_map = DEFAULT_HOTKEYS.copy()
        self.stop_polling = False
 
        self.create_widgets()
 
        if self.original_image_path:
            self.load_image(self.original_image_path)

        self.key_poll_thread = threading.Thread(target=poll_global_keys, args=(self,), daemon=True)
        self.key_poll_thread.start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def get_total_chunks(self):
        if not self.chunk_folder:
            return 0
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

        self.clickthrough_var = tk.BooleanVar()
        self.clickthrough_toggle = ttk.Checkbutton(mode_frame, text="Click-Through", variable=self.clickthrough_var, command=self.on_toggle_clickthrough)
        self.clickthrough_toggle.pack(side=RIGHT, expand=True)
 
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
        self.calibrate_button.config(state=NORMAL if enabled else DISABLED)
        if enabled:
            self.scale_slider.set(CALIBRATED_SCALE)

    def on_toggle_clickthrough(self):
        """Callback for click-through mode toggle."""
        if not self.image_window:
            self.clickthrough_var.set(False) # Ensure var is in a predictable state
            return
        self.image_window.toggle_clickthrough(self.clickthrough_var.get())

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
                x_min, y_min, width, height = selector.result
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
        self.num_chunks_x, self.num_chunks_y, self.total_chunks = split_image_into_chunks(
            self.original_image_path, self.chunk_folder
        )

        if self.image_window:
            self.image_window.destroy()
        self.image_window = ImageWindow(self, self.original_pil_image, self.num_chunks_x, self.num_chunks_y)
        
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