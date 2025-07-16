import tkinter as tk
from PIL import Image, ImageGrab, ImageTk
import time
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from control_window import ControlWindow

from config import ZOOM_FACTOR, ZOOM_AREA_SIZE, ZOOM_DISPLAY_SIZE, SCREENSHOT_DELAY

class CalibrationWindow(tk.Toplevel):
    """
    A modal fullscreen window for calibrating single chunk positioning.
    Handles screenshot capture, zoom view, and point selection.
    """
    def __init__(self, master: 'ControlWindow'):
        super().__init__(master)
        self.master: 'ControlWindow' = master  # Type annotation for master
        self.result: Optional[Tuple[int, int, int, int]] = None
        self.click_points = []
        self.preview_rect = None
        self.zoom_view_items = {}
        self.image_refs = {}
        
        # Take screenshot
        self.screenshot = self._capture_screenshot()
        
        self._setup_window()
        self._create_canvas()
        self._bind_events()
        
    def _capture_screenshot(self):
        """Captures a screenshot of the entire screen."""
        # Hide master windows to take a clean screenshot
        self.master.withdraw()
        
        # Type-safe access to image_window attribute
        if hasattr(self.master, 'image_window') and self.master.image_window:
            image_window = self.master.image_window
            if hasattr(image_window, 'state') and image_window.state() == 'normal':
                image_window.withdraw()
        
        self.master.update_idletasks()
        time.sleep(SCREENSHOT_DELAY)
        screenshot = ImageGrab.grab()
        
        # Restore master windows immediately
        self.master.deiconify()
        
        # Type-safe access to image_window and single_chunk_var attributes
        if hasattr(self.master, 'image_window') and self.master.image_window:
            image_window = self.master.image_window
            if (hasattr(image_window, 'state') and 
                image_window.state() == 'withdrawn' and 
                hasattr(self.master, 'single_chunk_var') and 
                self.master.single_chunk_var.get()):
                image_window.deiconify()
                
        return screenshot
    
    def _setup_window(self):
        """Configures the fullscreen modal window."""
        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)
        self.overrideredirect(True)
        self.grab_set()  # Make the window modal
        
    def _create_canvas(self):
        """Creates the canvas for displaying the screenshot and zoom view."""
        self.canvas = tk.Canvas(self, cursor='cross', bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Display the screenshot
        self.image_refs['screenshot'] = ImageTk.PhotoImage(self.screenshot)
        self.canvas.create_image(0, 0, image=self.image_refs['screenshot'], anchor='nw')
        
    def _bind_events(self):
        """Binds mouse and keyboard events."""
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.bind("<Escape>", self._on_cancel)
        
    def _update_zoom_view(self, event):
        """Updates the zoom view at the mouse position."""
        # Clear previous zoom view
        for item in self.zoom_view_items.values():
            self.canvas.delete(item)
        self.zoom_view_items.clear()
        
        # Calculate zoom view position
        view_x, view_y = event.x + 30, event.y + 30
        if view_x + ZOOM_DISPLAY_SIZE > self.winfo_width():
            view_x = event.x - ZOOM_DISPLAY_SIZE - 30
        if view_y + ZOOM_DISPLAY_SIZE > self.winfo_height():
            view_y = event.y - ZOOM_DISPLAY_SIZE - 30
            
        # Create zoomed image
        crop_box = (
            event.x - ZOOM_AREA_SIZE // 2,
            event.y - ZOOM_AREA_SIZE // 2,
            event.x + ZOOM_AREA_SIZE // 2,
            event.y + ZOOM_AREA_SIZE // 2
        )
        zoomed_img = self.screenshot.crop(crop_box).resize(
            (ZOOM_DISPLAY_SIZE, ZOOM_DISPLAY_SIZE), 
            Image.Resampling.NEAREST
        )
        
        # Display zoom view
        self.image_refs['zoom'] = ImageTk.PhotoImage(zoomed_img)
        self.zoom_view_items['image'] = self.canvas.create_image(
            view_x, view_y, image=self.image_refs['zoom'], anchor='nw'
        )
        self.zoom_view_items['box'] = self.canvas.create_rectangle(
            view_x, view_y, 
            view_x + ZOOM_DISPLAY_SIZE, view_y + ZOOM_DISPLAY_SIZE, 
            outline='cyan', width=2
        )
        
        # Draw crosshairs
        center_x, center_y = view_x + ZOOM_DISPLAY_SIZE // 2, view_y + ZOOM_DISPLAY_SIZE // 2
        self.zoom_view_items['cross_v'] = self.canvas.create_line(
            center_x, view_y, center_x, view_y + ZOOM_DISPLAY_SIZE, 
            fill='red', width=1
        )
        self.zoom_view_items['cross_h'] = self.canvas.create_line(
            view_x, center_y, view_x + ZOOM_DISPLAY_SIZE, center_y, 
            fill='red', width=1
        )
        
    def _draw_crosshair(self, x, y, size=10, color='cyan'):
        """Draws a crosshair at the specified position."""
        self.canvas.create_line(x - size, y, x + size, y, fill=color, width=2)
        self.canvas.create_line(x, y - size, x, y + size, fill=color, width=2)
        
    def _update_preview_rect(self, x2, y2):
        """Updates the preview rectangle between two points."""
        if len(self.click_points) != 1:
            return
            
        x1, y1 = self.click_points[0]
        if self.preview_rect:
            self.canvas.coords(self.preview_rect, x1, y1, x2, y2)
        else:
            self.preview_rect = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline='red', width=2
            )
            
    def _on_motion(self, event):
        """Handles mouse motion events."""
        self._update_zoom_view(event)
        if len(self.click_points) == 1:
            self._update_preview_rect(
                self.canvas.canvasx(event.x), 
                self.canvas.canvasy(event.y)
            )
            
    def _on_left_click(self, event):
        """Handles left mouse click events."""
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.click_points.append((x, y))
        self._draw_crosshair(x, y)
        
        if len(self.click_points) == 2:
            # Calculate the result rectangle
            (x1, y1), (x2, y2) = self.click_points
            x_min, y_min = min(x1, x2), min(y1, y2)
            width, height = abs(x2 - x1), abs(y2 - y1)
            
            if width > 0 and height > 0:
                self.result = (x_min, y_min, width, height)
            
            self.destroy()
            
    def _on_cancel(self, event):
        """Handles the escape key to cancel calibration."""
        self.destroy() 