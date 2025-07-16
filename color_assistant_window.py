import tkinter as tk
import ttkbootstrap as ttk
from tkinter import messagebox
from typing import List, Tuple, Optional, TYPE_CHECKING
from collections import defaultdict

# Import the NEW function and remove the old one
from ttkbootstrap.scrolled import ScrolledFrame

if TYPE_CHECKING:
    from control_window import ControlWindow

# A predefined set of primary colors for grouping is no longer needed

class ColorAssistantWindow(tk.Toplevel):
    """
    A window to display common colors, now with controls to find and filter them.
    Colors are grouped by their nearest primary color.
    """
    def __init__(self, master: 'ControlWindow', image_path: str):
        super().__init__(master)
        self.master: 'ControlWindow' = master
        self.image_path = image_path
        self.selected_colors: List[Tuple[int, int, int]] = []
        self.colors: List[Tuple[int, int, int]] = []
        self.swatches = {}
        self.pane_to_container_map = {}

        # --- User-configurable variables ---
        self.automated_mode = tk.BooleanVar(value=False)
        self.drawing_speed = tk.DoubleVar(value=0.1)
        self.color_tolerance = tk.IntVar(value=10)
        # We no longer need 'grouping_tolerance'. We control the number of groups directly.
        self.num_colors_to_find = tk.IntVar(value=10) # Default to 10 groups

        self._setup_window()
        self._create_widgets()
        self.after(50, self._update_color_swatches)

    def _setup_window(self):
        """Configures the window's properties."""
        self.title("Color Assistant")
        self.geometry("380x600")
        self.resizable(True, True)
        self.transient(self.master)
        self.grab_set()
        
    def _create_widgets(self):
        """Creates and places the widgets in the window."""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- Section 1: Find Colors ---
        find_frame = ttk.Labelframe(main_frame, text="1. Find Color Groups", padding=10)
        find_frame.pack(pady=(0, 10), fill=tk.X)
        
        num_colors_frame = ttk.Frame(find_frame)
        num_colors_frame.pack(fill=tk.X, expand=True, pady=(0, 5))
        ttk.Label(num_colors_frame, text="Number of Groups:").pack(side=tk.LEFT)
        self.num_colors_label = ttk.Label(num_colors_frame, text=f"{self.num_colors_to_find.get()}", width=3)
        self.num_colors_label.pack(side=tk.RIGHT, padx=(5,0))
        ttk.Scale(
            num_colors_frame, from_=2, to=30, variable=self.num_colors_to_find, orient=tk.HORIZONTAL,
            command=lambda v: self.num_colors_label.config(text=f"{int(float(v))}")
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Button(
            find_frame, text="Refresh Colors", command=self._update_color_swatches, style="info.TButton"
        ).pack(pady=5)

        # --- Section 2: Select Colors (Scrollable) ---
        select_frame = ttk.Labelframe(main_frame, text="2. Select Colors", padding=10)
        select_frame.pack(pady=(0, 10), fill=tk.BOTH, expand=True)
        
        self.color_frame = ScrolledFrame(select_frame, autohide=True)
        self.color_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- Section 3: Drawing Settings ---
        drawing_frame = ttk.Labelframe(main_frame, text="3. Drawing Settings", padding=10)
        drawing_frame.pack(pady=(0, 10), fill=tk.X)
        
        # Automated mode toggle
        self.automated_checkbox = ttk.Checkbutton(
            drawing_frame, text="Automated Drawing Mode", variable=self.automated_mode
        )
        self.automated_checkbox.pack(anchor=tk.W, pady=2)
        
        # Drawing speed slider
        speed_frame = ttk.Frame(drawing_frame)
        speed_frame.pack(fill=tk.X, pady=2)
        ttk.Label(speed_frame, text="Drawing Speed (seconds):").pack(side=tk.LEFT)
        speed_label = ttk.Label(speed_frame, text=f"{self.drawing_speed.get():.1f}", width=5)
        speed_label.pack(side=tk.RIGHT)
        ttk.Scale(
            speed_frame, from_=0.05, to=1.0, variable=self.drawing_speed, orient=tk.HORIZONTAL,
            command=lambda v: speed_label.config(text=f"{float(v):.1f}")
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Color tolerance slider
        tolerance_frame = ttk.Frame(drawing_frame)
        tolerance_frame.pack(fill=tk.X, pady=2)
        ttk.Label(tolerance_frame, text="Color Tolerance:").pack(side=tk.LEFT)
        tolerance_label = ttk.Label(tolerance_frame, text=f"{self.color_tolerance.get()}", width=3)
        tolerance_label.pack(side=tk.RIGHT)
        ttk.Scale(
            tolerance_frame, from_=0, to=50, variable=self.color_tolerance, orient=tk.HORIZONTAL,
            command=lambda v: tolerance_label.config(text=f"{int(float(v))}")
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # --- Bottom Info and Action ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))
        
        self.selected_color_label = ttk.Label(bottom_frame, text="Selected: 0 colors")
        self.selected_color_label.pack(pady=5)

        ttk.Button(
            bottom_frame, text="Apply & Close", command=self._confirm_selection, style="success.TButton"
        ).pack(pady=5, fill=tk.X)
            
    def _update_color_swatches(self):
        """Finds and groups colors using K-means and updates the UI."""
        for widget in self.color_frame.winfo_children():
            widget.destroy()
        self.swatches.clear()
        self.pane_to_container_map.clear()

        try:
            # Call our new, improved function
            num_groups = self.num_colors_to_find.get()
            from image_utils import extract_and_group_colors_kmeans
            grouped_colors = extract_and_group_colors_kmeans(self.image_path, num_colors=num_groups)
        except Exception as e:
            messagebox.showerror("Error", f"Could not extract colors: {e}")
            return

        # The rest of the function is the same as before, as it just displays the groups
        for group_name, colors_in_group in sorted(grouped_colors.items()):
            if not colors_in_group:
                continue

            pane = ttk.Frame(self.color_frame, padding=5)
            pane.pack(fill=tk.X, pady=2)

            header_frame = ttk.Frame(pane)
            header_frame.pack(fill=tk.X)

            btn_toggle = ttk.Button(header_frame, text=f"▼ {group_name} ({len(colors_in_group)})", style="Link.TButton")
            btn_toggle.pack(side=tk.LEFT)
            btn_toggle.config(command=lambda p=pane, b=btn_toggle: self._toggle_pane(p, b))

            swatch_container = ttk.Frame(pane)
            swatch_container.pack(fill=tk.X, padx=10, pady=5)
            self.pane_to_container_map[pane] = swatch_container

            max_swatches_per_row = 5
            for i, color in enumerate(colors_in_group):
                row = i // max_swatches_per_row
                col = i % max_swatches_per_row

                if col == 0:
                    row_frame = ttk.Frame(swatch_container)
                    row_frame.pack(fill=tk.X, pady=2)

                rgb_hex = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                swatch = tk.Canvas(
                    row_frame, width=40, height=30, cursor="hand2",
                    highlightthickness=2, highlightbackground="#4f4f4f"
                )
                swatch.pack(side=tk.LEFT, padx=5)
                swatch.create_rectangle(0, 0, 40, 30, fill=rgb_hex, outline="")
                swatch.bind("<Button-1>", lambda e, c=color: self._on_color_select(c))
                self.swatches[color] = swatch

    def _toggle_pane(self, pane: ttk.Frame, button: ttk.Button):
        """Shows or hides the swatch container within a pane."""
        container = self.pane_to_container_map.get(pane)
        if not container:
            return

        # button = pane.winfo_children()[0].winfo_children()[0] # Yuck, but effective
        
        if container.winfo_viewable():
            container.pack_forget()
            button.config(text=button.cget('text').replace('▼', '►'))
        else:
            container.pack(fill=tk.X, padx=10, pady=5)
            button.config(text=button.cget('text').replace('►', '▼'))

    def _on_color_select(self, color: Tuple[int, int, int]):
        """Handles toggling color selection and provides visual feedback."""
        swatch = self.swatches.get(color)
        if not swatch: return

        if color in self.selected_colors:
            self.selected_colors.remove(color)
            swatch.config(highlightbackground="#4f4f4f")
        else:
            self.selected_colors.append(color)
            swatch.config(highlightbackground="cyan")

        num_selected = len(self.selected_colors)
        self.selected_color_label.config(text=f"Selected: {num_selected} color{'s' if num_selected != 1 else ''}")

    def _confirm_selection(self):
        """Confirms the selection and closes the window."""
        if not self.selected_colors:
            messagebox.showwarning("No Color Selected", "Please select one or more colors or close the window.")
            return
        
        self.destroy() 