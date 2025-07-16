"""
Utility functions for image processing operations.
Centralizes image splitting and other image-related functionality.
"""
import os
from PIL import Image
from config import CHUNK_SIZE

def split_image_into_chunks(image_path, output_folder):
    """
    Splits an image into smaller chunks and saves them to the specified folder.
    
    Args:
        image_path (str): Path to the source image
        output_folder (str): Folder to save the chunks in
        
    Returns:
        tuple: (num_chunks_x, num_chunks_y, total_chunks)
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
        
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    # Load image
    image = Image.open(image_path)
    img_w, img_h = image.size
    
    # Calculate grid dimensions
    num_chunks_x = (img_w + CHUNK_SIZE - 1) // CHUNK_SIZE
    num_chunks_y = (img_h + CHUNK_SIZE - 1) // CHUNK_SIZE
    total_chunks = num_chunks_x * num_chunks_y
    
    # Split and save chunks
    chunk_index = 0
    for y in range(0, img_h, CHUNK_SIZE):
        for x in range(0, img_w, CHUNK_SIZE):
            chunk_box = (x, y, x + CHUNK_SIZE, y + CHUNK_SIZE)
            chunk_img = image.crop(chunk_box)
            chunk_path = os.path.join(output_folder, f"chunk_{chunk_index}.png")
            chunk_img.save(chunk_path)
            chunk_index += 1
    
    return num_chunks_x, num_chunks_y, total_chunks

def get_chunk_info(image_path):
    """
    Gets information about how an image would be split into chunks.
    
    Args:
        image_path (str): Path to the image
        
    Returns:
        tuple: (num_chunks_x, num_chunks_y, total_chunks)
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
        
    image = Image.open(image_path)
    img_w, img_h = image.size
    
    num_chunks_x = (img_w + CHUNK_SIZE - 1) // CHUNK_SIZE
    num_chunks_y = (img_h + CHUNK_SIZE - 1) // CHUNK_SIZE
    total_chunks = num_chunks_x * num_chunks_y
    
    return num_chunks_x, num_chunks_y, total_chunks

def count_existing_chunks(output_folder):
    """
    Counts the number of existing chunk files in a folder.
    
    Args:
        output_folder (str): Folder containing chunk files
        
    Returns:
        int: Number of chunk files found
    """
    if not os.path.exists(output_folder):
        return 0
        
    import glob
    search_path = os.path.join(output_folder, "chunk_*.png")
    files = glob.glob(search_path)
    return len(files) 