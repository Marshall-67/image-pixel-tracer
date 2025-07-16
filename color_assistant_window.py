import tkinter as tk
from tkinter import messagebox
from typing import List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from control_window import ControlWindow

class ColorAssistantWindow(tk.Toplevel):
    """
    A window to display common colors and allow the user to select one.
    """
    def __init__(self, master: 'ControlWindow', colors: List[Tuple[int, int, int]]):
        super().__init__(master)
        self.master: 'ControlWindow' = master
        self.selected_color: Optional[Tuple[int, int, int]] = None
        self.colors = colors
        
        self._setup_window()
        self._create_widgets()
        
    def _setup_window(self):
        """Configures the window's properties."""
        self.title("Color Assistant")
        self.geometry("300x150")
        self.resizable(False, False)
        self.transient(self.master)
        self.grab_set()
        
    def _create_widgets(self):
        """Creates and places the widgets in the window."""
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        label = tk.Label(main_frame, text="Select a color to highlight:")
        label.pack(pady=(0, 10))
        
        color_frame = tk.Frame(main_frame)
        color_frame.pack()
        
        for color in self.colors:
            rgb_hex = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            
            # Using a small Canvas to draw the color swatch for reliable color display
            swatch_canvas = tk.Canvas(
                color_frame,
                width=40,
                height=30,
                bg='white',  # Default background in case of error
                highlightthickness=1,
                highlightbackground='gray',
                cursor="hand2"
            )
            swatch_canvas.pack(side=tk.LEFT, padx=5)
            
            # Draw the color rectangle
            swatch_canvas.create_rectangle(0, 0, 40, 30, fill=rgb_hex, outline='')
            
            # Bind click event
            swatch_canvas.bind("<Button-1>", lambda e, c=color: self._on_color_select(c))
            
    def _on_color_select(self, color: Tuple[int, int, int]):
        """Handles the event when a color is selected."""
        self.selected_color = color
        self.destroy() 