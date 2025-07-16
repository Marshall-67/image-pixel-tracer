import sys
from control_window import ControlWindow

def main():
    """
    Main entry point for the application.

    Usage:
        python main.py [<image_path>]

    If an image path is provided, the application will load it immediately.
    Otherwise, the user can select an image from within the GUI via the
    new "Load Image" button.
    """
    original_image_path = sys.argv[1] if len(sys.argv) >= 2 else None
    app = ControlWindow(original_image_path=original_image_path)
    app.mainloop()

if __name__ == "__main__":
    main()
