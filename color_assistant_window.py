import tkinter as tk
import ttkbootstrap as ttk
from tkinter import messagebox
from typing import List, Tuple, Optional, TYPE_CHECKING
from collections import defaultdict

from collections import defaultdict

# Import our new, improved function
from image_utils import extract_color_groups
from ttkbootstrap.scrolled import ScrolledFrame

if TYPE_CHECKING:
    from control_window import ControlWindow

class ColorAssistantWindow(tk.Toplevel):
    """
    A window to display common colors, now with controls to find and filter them.
    Colors are grouped by their nearest primary color.
    """
    def __init__(self, master: 'ControlWindow', image_path: str, settings: dict):
        super().__init__(master)
        self.master: 'ControlWindow' = master
        self.image_path = image_path
        self.was_confirmed = False # Flag to check if "Apply" was clicked
        self.selected_colors: List[Tuple[int, int, int]] = []
        self.colors: List[Tuple[int, int, int]] = []
        self.swatches = {}
        self.pane_to_container_map = {}

        # --- Use passed-in settings with .get() for safety ---
        self.automated_mode = tk.BooleanVar(value=settings.get('automated_mode', False))
        self.drawing_speed = tk.DoubleVar(value=settings.get('drawing_speed', 0.05))
        self.color_tolerance = tk.IntVar(value=settings.get('color_tolerance', 10))
        self.grouping_sensitivity = tk.DoubleVar(value=settings.get('grouping_sensitivity', 10.0))
        self.double_click = tk.BooleanVar(value=settings.get('double_click', False))

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
        
        # --- NEW WIDGETS for DBSCAN sensitivity ---
        sensitivity_frame = ttk.Frame(find_frame)
        sensitivity_frame.pack(fill=tk.X, expand=True, pady=(0, 5))
        ttk.Label(sensitivity_frame, text="Grouping Detail:").pack(side=tk.LEFT, anchor='w')
        
        sensitivity_label = ttk.Label(sensitivity_frame, text=f"{self.grouping_sensitivity.get():.1f}", width=4)
        sensitivity_label.pack(side=tk.RIGHT, padx=(5,0))
        
        # Note the reversed scale: sliding right lowers `eps`, which means MORE detail.
        ttk.Scale(
            sensitivity_frame, from_=20.0, to=2.0,
            variable=self.grouping_sensitivity,
            orient=tk.HORIZONTAL,
            command=lambda v: sensitivity_label.config(text=f"{float(v):.1f}")
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        helper_label = ttk.Label(find_frame, text="← Less Groups  |  More Groups →", font=("Segoe UI", 7))
        helper_label.pack(fill=tk.X, pady=(0, 5), padx=5)

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
        
        # Double click checkbox
        self.double_click_checkbox = ttk.Checkbutton(
            drawing_frame, text="Double Click", variable=self.double_click
        )
        self.double_click_checkbox.pack(anchor=tk.W, pady=2)

        # Drawing speed slider
        speed_frame = ttk.Frame(drawing_frame)
        speed_frame.pack(fill=tk.X, pady=2)
        ttk.Label(speed_frame, text="Drawing Speed (seconds):").pack(side=tk.LEFT)
        speed_label = ttk.Label(speed_frame, text=f"{self.drawing_speed.get():.2f}", width=5)
        speed_label.pack(side=tk.RIGHT)
        ttk.Scale(
            speed_frame, from_=0.01, to=1.0, variable=self.drawing_speed, orient=tk.HORIZONTAL,
            command=lambda v: speed_label.config(text=f"{float(v):.2f}")
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
        """Finds and groups colors using DBSCAN and updates the UI."""
        for widget in self.color_frame.winfo_children():
            widget.destroy()
        self.swatches.clear()
        self.pane_to_container_map.clear()

        try:
            # Call our new, improved function with the sensitivity parameter
            sensitivity = self.grouping_sensitivity.get()
            grouped_colors = extract_color_groups(self.image_path, eps=sensitivity)
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

            btn_select_all = ttk.Button(
                header_frame, text="Select All", style="Outline.TButton",
                command=lambda g=colors_in_group: self._toggle_group_selection(g)
            )
            btn_select_all.pack(side=tk.RIGHT)

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

    def _toggle_group_selection(self, colors_in_group: List[Tuple[int, int, int]]):
        """Selects or deselects all colors in a given group."""
        # Check if any color in the group is already selected
        is_any_selected = any(c in self.selected_colors for c in colors_in_group)

        if is_any_selected:
            # If any are selected, deselect the entire group
            for color in colors_in_group:
                if color in self.selected_colors:
                    self._on_color_select(color) # This will toggle it off
        else:
            # If none are selected, select the entire group
            for color in colors_in_group:
                if color not in self.selected_colors:
                    self._on_color_select(color) # This will toggle it on

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
        if self.automated_mode.get() and not self.selected_colors:
            messagebox.showwarning("No Color Selected", "Please select one or more colors for automated drawing.")
            return
        
        self.was_confirmed = True # Set the flag
        self.destroy()