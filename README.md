# Dither-it

A tool for overlaying dithered images on your screen. Useful for pixel art, cross-stitch patterns, or any grid-based artwork.

## What it does

Load an image and it gets split into 32x32 pixel chunks. You can navigate through chunks, adjust opacity and scale, and position them precisely on your screen. The overlay stays on top of other windows and can be made click-through so you can work underneath it.

## Features

- **Chunk Navigation**: Browse through image chunks with arrow keys or slider
- **Opacity Control**: Adjust transparency with +/- keys
- **Zoom**: Scale chunks up to 15x with Ctrl + +/-
- **Click-through Mode**: Work underneath the overlay
- **Single Chunk Mode**: Focus on one chunk with precise positioning
- **Calibration**: Fullscreen mode for exact positioning
- **Global Hotkeys**: Control everything without switching windows

## Quick Start

1. Run the app: `python main.py`
2. Load an image using the "Load Image" button
3. Use arrow keys to navigate chunks
4. Press Insert to toggle the overlay on/off

## Controls

| Key | Action |
|-----|--------|
| Insert | Toggle overlay visibility |
| Arrow Keys | Next/previous chunk |
| +/- | Adjust opacity |
| Ctrl + +/- | Zoom in/out |
| R | Reset scale |
| S | Toggle single chunk mode |
| C | Toggle click-through |

## Single Chunk Mode

Perfect for detailed work:
1. Enable "Single Chunk Mode"
2. Click "Calibrate" for precise positioning
3. Use the fullscreen calibration to place the chunk exactly where you need it

## Requirements

- Python 3.7+
- Windows (uses win32api for global hotkeys)
- PIL/Pillow
- ttkbootstrap
- pywin32

## Installation

```bash
pip install pillow ttkbootstrap pywin32
```

## Usage

```bash
# Start with no image
python main.py

# Start with an image
python main.py path/to/image.png
```

## Building

To create an executable:

```bash
pip install pyinstaller
pyinstaller main.spec
```

The exe will be in `dist/main/`.

---

Made by Bob&Bill Inc 