import tkinter as tk
from PIL import Image, ImageTk
import win32gui

from config import (
    CHUNK_SIZE, DEFAULT_ALPHA, DEFAULT_SCALE, CALIBRATED_SCALE,
    GRID_COLOR_FULL, GRID_COLOR_PIXEL, HIGHLIGHT_COLOR, TRANSPARENT_COLOR, SUCCESS_COLOR,
    DEFAULT_WINDOW_X, DEFAULT_WINDOW_Y, MIN_SCALE, MAX_SCALE, MIN_ALPHA, MAX_ALPHA
)
from win_utils import set_clickthrough
from image_utils import colors_are_similar

class ImageWindow(tk.Toplevel):
    """
    A floating, borderless window that displays the image, grid, and highlight.
    This window is controlled by the main ControlWindow.
    """
    def __init__(self, master, original_image, num_chunks_x, num_chunks_y):
        super().__init__(master)
        self.original_pil_image = original_image
        self.num_chunks_x = num_chunks_x
        self.num_chunks_y = num_chunks_y

        # Window state
        self.alpha = DEFAULT_ALPHA
        self.scale_factor = DEFAULT_SCALE
        self.clickthrough_mode = False
        self.single_chunk_mode = False
        self.current_chunk_index = 0
        self.calibrated_scale = CALIBRATED_SCALE  # Default
        
        # Image caching for performance
        self.chunk_cache = {}

        # Calibration
        self.target_x = None
        self.target_y = None
        self.target_w = None
        self.target_h = None

        # Highlighting
        self.highlighted_colors = []
        self.highlight_rects = []
        self.highlight_tolerance = 0
        self.success_markers = []

        # Image dimensions
        self.original_width, self.original_height = self.original_pil_image.size
        self.img_width = self.original_width
        self.img_height = self.original_height
        
        # For moving the window
        self._x = 0
        self._y = 0

        self.setup_window()
        self.create_widgets()
        self.bind_events()
        
        self.after(100, self.initialize_win32)

    def initialize_win32(self):
        """Initializes pywin32 properties after the window is created."""
        try:
            self.hwnd = win32gui.GetParent(self.winfo_id())
            # First, establish the layered window with alpha but NO clickthrough.
            # This creates a stable base state for the window.
            set_clickthrough(self.hwnd, self.alpha, False)

            # If the user toggled click-through ON before this init ran,
            # we now safely apply the transparent style to the stable window.
            if self.clickthrough_mode:
                set_clickthrough(self.hwnd, self.alpha, True)
                
        except Exception as e:
            print(f"Error during win32 initialization for ImageWindow: {e}")

    def setup_window(self):
        """Configures the window properties for a borderless overlay."""
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry(f"+{DEFAULT_WINDOW_X}+{DEFAULT_WINDOW_Y}")
        
        self.config(bg=TRANSPARENT_COLOR)
        self.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)

    def create_widgets(self):
        """Creates the canvas for drawing."""
        self.canvas = tk.Canvas(
            self,
            width=self.img_width,
            height=self.img_height,
            bg=self.cget('bg'), # Use the same transparent color as the window
            bd=0,
            highlightthickness=0
        )
        self.canvas.pack()

    def bind_events(self):
        """Binds mouse events for moving the window."""
        self.canvas.bind("<ButtonPress-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.do_move)

    def update_display(self):
        """Updates the canvas size and redraws all elements."""
        if self.single_chunk_mode:
            # In single chunk mode, we resize the image to fit the target area,
            # preserving aspect ratio, and then size the window and canvas to match.
            chunk_w, chunk_h = self.get_current_chunk_size()

            if self.target_w is not None and self.target_h is not None and \
               self.target_x is not None and self.target_y is not None and \
               chunk_w > 0 and chunk_h > 0:
                # Fit the chunk into the target area, preserving aspect ratio
                scale = min(self.target_w / chunk_w, self.target_h / chunk_h)
                self.img_width = int(chunk_w * scale)
                self.img_height = int(chunk_h * scale)
                
                # Center the now smaller window within the original target area
                win_x = self.target_x + (self.target_w - self.img_width) // 2
                win_y = self.target_y + (self.target_h - self.img_height) // 2
                self.geometry(f"{self.img_width}x{self.img_height}+{win_x}+{win_y}")
            else:
                # Fallback if not calibrated: use a default scale
                self.img_width = int(chunk_w * self.calibrated_scale)
                self.img_height = int(chunk_h * self.calibrated_scale)
                # Position it at the last known good coordinates or a default
                last_x = self.winfo_x()
                last_y = self.winfo_y()
                self.geometry(f"{self.img_width}x{self.img_height}+{last_x}+{last_y}")
        else:
            self.img_width = int(self.original_width * self.scale_factor)
            self.img_height = int(self.original_height * self.scale_factor)

        self.canvas.config(width=self.img_width, height=self.img_height)
        self.canvas.delete("all")
        self.draw_canvas_elements()
        self.update_idletasks()

    def draw_canvas_elements(self):
        """Draws the image, grid, and highlight."""
        if self.single_chunk_mode:
            self.draw_single_chunk()
        else:
            self.draw_full_image_with_grid()
        
        self.draw_highlight()
        if self.highlighted_colors:
            self.draw_color_highlights()
        self.draw_success_markers()

    def draw_single_chunk(self):
        """Draws the current chunk enlarged to fit the calibrated area."""
        chunk_w, chunk_h = self.get_current_chunk_size()
        if chunk_w == 0 or chunk_h == 0:
            return

        # Check cache first
        if self.current_chunk_index in self.chunk_cache:
            self.tk_image = self.chunk_cache[self.current_chunk_index]
        else:
            # Crop the original image to the current chunk
            row = self.current_chunk_index // self.num_chunks_x
            col = self.current_chunk_index % self.num_chunks_x
            x1 = col * CHUNK_SIZE
            y1 = row * CHUNK_SIZE
            x2 = min(x1 + CHUNK_SIZE, self.original_width)
            y2 = min(y1 + CHUNK_SIZE, self.original_height)
            chunk_image = self.original_pil_image.crop((x1, y1, x2, y2))
            
            # Resize chunk to fit the canvas, which has been pre-sized by update_display
            if self.img_width <= 0 or self.img_height <= 0:
                return

            scaled_chunk = chunk_image.resize((self.img_width, self.img_height), Image.Resampling.NEAREST)
            self.tk_image = ImageTk.PhotoImage(scaled_chunk)
            # Save to cache
            self.chunk_cache[self.current_chunk_index] = self.tk_image

        # The canvas is the same size as the image, so we draw at the center
        self.canvas.create_image(self.img_width // 2, self.img_height // 2, anchor='center', image=self.tk_image)
        
        # Draw the pixel grid over the image
        pixel_size = self.img_width / chunk_w
        self.draw_pixel_grid(0, 0, chunk_w, chunk_h, pixel_size)

    def draw_color_highlights(self):
        """Highlights pixels of specific colors."""
        if not self.single_chunk_mode or not self.highlighted_colors:
            return

        chunk_w, chunk_h = self.get_current_chunk_size()
        if chunk_w == 0 or chunk_h == 0:
            return
            
        row = self.current_chunk_index // self.num_chunks_x
        col = self.current_chunk_index % self.num_chunks_x
        x1 = col * CHUNK_SIZE
        y1 = row * CHUNK_SIZE
        x2 = min(x1 + CHUNK_SIZE, self.original_width)
        y2 = min(y1 + CHUNK_SIZE, self.original_height)
        
        chunk_image = self.original_pil_image.crop((x1, y1, x2, y2)).convert("RGB")
        pixel_data = chunk_image.load()
        
        pixel_size = self.img_width / chunk_w
        
        # The primary color for filling is the first one in the list
        r_fill, g_fill, b_fill = self.highlighted_colors[0]
        
        for y_local in range(chunk_h):
            for x_local in range(chunk_w):
                r, g, b = pixel_data[x_local, y_local]
                
                # Check if the pixel matches any of the selected colors
                for target_color in self.highlighted_colors:
                    if colors_are_similar((r, g, b), target_color, self.highlight_tolerance):
                        rx1 = x_local * pixel_size
                        ry1 = y_local * pixel_size
                        rx2 = rx1 + pixel_size
                        ry2 = ry1 + pixel_size
                        rect = self.canvas.create_rectangle(
                            rx1, ry1, rx2, ry2, 
                            fill=f"#{r_fill:02x}{g_fill:02x}{b_fill:02x}", 
                            outline="red", 
                            width=1
                        )
                        self.highlight_rects.append(rect)
                        break # Found a match, no need to check other colors

    def draw_pixel_grid(self, img_x, img_y, chunk_w, chunk_h, pixel_size):
        """Draws a pixel grid on the enlarged chunk."""
        scaled_w = int(chunk_w * pixel_size)
        scaled_h = int(chunk_h * pixel_size)
        for i in range(1, chunk_w):
            x = img_x + i * pixel_size
            if x < img_x + scaled_w:
                self.canvas.create_line(x, img_y, x, img_y + scaled_h, fill=GRID_COLOR_PIXEL, width=1)
        for i in range(1, chunk_h):
            y = img_y + i * pixel_size
            if y < img_y + scaled_h:
                self.canvas.create_line(img_x, y, img_x + scaled_w, y, fill=GRID_COLOR_PIXEL, width=1)

    def draw_full_image_with_grid(self):
        """Draws the full image with the chunk grid."""
        scaled_image = self.original_pil_image.resize(
            (self.img_width, self.img_height), 
            Image.Resampling.NEAREST
        )
        self.tk_image = ImageTk.PhotoImage(scaled_image)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

        scaled_chunk_size = CHUNK_SIZE * self.scale_factor
        for i in range(1, self.num_chunks_x):
            x = i * scaled_chunk_size
            self.canvas.create_line(x, 0, x, self.img_height, fill=GRID_COLOR_FULL, dash=(2, 4))
        for i in range(1, self.num_chunks_y):
            y = i * scaled_chunk_size
            self.canvas.create_line(0, y, self.img_width, y, fill=GRID_COLOR_FULL, dash=(2, 4))

    def draw_highlight(self):
        """Draws the highlight rectangle over the current chunk."""
        if self.single_chunk_mode:
            return # No highlight needed when only one chunk is visible

        scaled_chunk_w = CHUNK_SIZE * self.scale_factor
        scaled_chunk_h = CHUNK_SIZE * self.scale_factor
        
        row = self.current_chunk_index // self.num_chunks_x
        col = self.current_chunk_index % self.num_chunks_x
        
        x1 = col * scaled_chunk_w
        y1 = row * scaled_chunk_h
        x2 = x1 + scaled_chunk_w
        y2 = y1 + scaled_chunk_h
        
        self.canvas.create_rectangle(x1, y1, x2, y2, outline=HIGHLIGHT_COLOR, width=2)
        
    # --- Public methods for ControlWindow to call ---
    def highlight_colors(self, colors, tolerance=0):
        """Sets the colors to be highlighted."""
        self.highlighted_colors = colors
        self.highlight_tolerance = tolerance
        self.update_display()

    def clear_color_highlight(self):
        """Clears any color highlighting and success markers."""
        for rect in self.highlight_rects:
            self.canvas.delete(rect)
        self.highlight_rects.clear()
        self.highlighted_colors = []
        
        self.clear_success_markers() # <-- Add this call
        
        self.update_display()



    def mark_pixel_as_successful(self, screen_x, screen_y):
        """Draws a visual marker on a successfully drawn pixel."""
        # Convert absolute screen coordinates to local canvas coordinates
        canvas_x = screen_x - self.winfo_x()
        canvas_y = screen_y - self.winfo_y()

        # Draw a small, semi-transparent circle or rectangle as a marker
        # We'll use a 3x3 rectangle for visibility
        marker = self.canvas.create_rectangle(
            canvas_x - 1, canvas_y - 1,
            canvas_x + 1, canvas_y + 1,
            outline=SUCCESS_COLOR,
            fill=SUCCESS_COLOR,
            width=1
        )
        self.success_markers.append(marker)
    
    def draw_success_markers(self):
        """Redraws all success markers (needed if the display updates)."""
        # This is a placeholder; a more robust implementation might re-calculate
        # marker positions if the window moves during drawing, but for now,
        # we assume it's static during the drawing process. The primary
        # use is to ensure they are drawn on top.
        for marker in self.success_markers:
            self.canvas.tag_raise(marker)

    def clear_success_markers(self):
        """Clears all visual success markers from the canvas."""
        for marker in self.success_markers:
            self.canvas.delete(marker)
        self.success_markers.clear()

    def get_pixel_locations_for_colors(self, target_colors):
        """
        Gets the absolute screen coordinates for all pixels in the current chunk
        that match any of the target colors.
        """
        if not self.single_chunk_mode or not target_colors:
            return []

        # Ensure the window is placed correctly before getting locations
        self.update_display()
        self.update_idletasks()
        
        win_x = self.winfo_x()
        win_y = self.winfo_y()

        chunk_w, chunk_h = self.get_current_chunk_size()
        if chunk_w == 0 or chunk_h == 0:
            return []

        row = self.current_chunk_index // self.num_chunks_x
        col = self.current_chunk_index % self.num_chunks_x
        x1 = col * CHUNK_SIZE
        y1 = row * CHUNK_SIZE
        x2 = min(x1 + CHUNK_SIZE, self.original_width)
        y2 = min(y1 + CHUNK_SIZE, self.original_height)
        
        try:
            chunk_image = self.original_pil_image.crop((x1, y1, x2, y2)).convert("RGB")
            pixel_data = chunk_image.load()
        except Exception as e:
            print(f"Error getting chunk image data: {e}")
            return []

        locations = []
        pixel_w = self.img_width / chunk_w
        pixel_h = self.img_height / chunk_h

        for y_local in range(chunk_h):
            for x_local in range(chunk_w):
                r, g, b = pixel_data[x_local, y_local]
                
                for target_color in target_colors:
                    if colors_are_similar((r, g, b), target_color, self.highlight_tolerance):
                        # Calculate center of the scaled pixel on the canvas
                        canvas_x = x_local * pixel_w + (pixel_w / 2)
                        canvas_y = y_local * pixel_h + (pixel_h / 2)
                        
                        # Convert to absolute screen coordinates
                        screen_x = win_x + canvas_x
                        screen_y = win_y + canvas_y
                        
                        locations.append((int(screen_x), int(screen_y)))
                        break # Found a match, move to the next pixel

        return locations

    def set_alpha(self, value):
        """Sets the window's alpha/opacity."""
        self.alpha = max(MIN_ALPHA, min(MAX_ALPHA, float(value)))
        if hasattr(self, 'hwnd'):
            set_clickthrough(self.hwnd, self.alpha, self.clickthrough_mode)
        else:
            # If hwnd isn't initialized yet, schedule the alpha update for after initialization
            self.after(150, lambda: self._apply_alpha_if_ready())

    def _apply_alpha_if_ready(self):
        """Applies the current alpha value if the window handle is ready."""
        if hasattr(self, 'hwnd'):
            set_clickthrough(self.hwnd, self.alpha, self.clickthrough_mode)

    def set_scale(self, value):
        self.scale_factor = value
        self.update_display()

    def set_chunk(self, index):
        self.current_chunk_index = index
        self.update_display()
        
    def clear_cache(self):
        """Clears the chunk cache to free memory."""
        self.chunk_cache.clear()

    def toggle_clickthrough(self, enabled):
        self.clickthrough_mode = enabled
        if hasattr(self, 'hwnd'):
            set_clickthrough(self.hwnd, self.alpha, self.clickthrough_mode)

    def toggle_single_chunk(self, enabled):
        self.single_chunk_mode = enabled
        if not enabled:
            self.clear_color_highlight()
        self.update_display()
        self.clear_cache()
        # Reset scale when exiting single chunk mode
        if not enabled and self.master:
            self.set_scale(self.calibrated_scale)  # Use calibrated scale

    def set_calibration(self, x, y, w, h):
        """Sets the position and size of the chunk window based on calibration."""
        self.target_x = int(x)
        self.target_y = int(y)
        self.target_w = int(w)
        self.target_h = int(h)

        # Calculate the new scale based on the selection
        chunk_w, chunk_h = self.get_current_chunk_size()
        if chunk_w > 0 and chunk_h > 0:
            scale_x = self.target_w / chunk_w
            scale_y = self.target_h / chunk_h
            self.calibrated_scale = min(scale_x, scale_y)

        # Move the window via update_display, which now handles positioning
        if self.single_chunk_mode:
            self.update_display()
        else:
            # If not in single chunk mode, still move the window to the top-left of the target
             self.geometry(f"+{self.target_x}+{self.target_y}")

    def start_move(self, event):
        self._x = event.x_root - self.winfo_x()
        self._y = event.y_root - self.winfo_y()

    def do_move(self, event):
        x = event.x_root - self._x
        y = event.y_root - self._y
        self.geometry(f"+{x}+{y}")

    def toggle_visibility(self):
        """Hides or shows the image window."""
        if self.state() == 'normal':
            self.withdraw()
        else:
            self.deiconify()
    def get_current_chunk_size(self):
        row = self.current_chunk_index // self.num_chunks_x
        col = self.current_chunk_index % self.num_chunks_x
        x1 = col * CHUNK_SIZE
        y1 = row * CHUNK_SIZE
        x2 = min(x1 + CHUNK_SIZE, self.original_width)
        y2 = min(y1 + CHUNK_SIZE, self.original_height)
        return x2 - x1, y2 - y1
