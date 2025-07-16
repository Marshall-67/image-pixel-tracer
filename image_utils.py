"""
Utility functions for image processing operations.
Centralizes image splitting and other image-related functionality.
"""
import os
from PIL import Image
from config import CHUNK_SIZE
import numpy as np
from sklearn.cluster import KMeans

def extract_common_colors(image_path, num_colors=5):
    """
    Extracts the most common colors from an image.
    If the image has fewer unique colors than requested, all unique colors are returned.
    Otherwise, k-means clustering is used to find the dominant colors.
    
    Args:
        image_path (str): Path to the source image.
        num_colors (int): Number of common colors to extract.
        
    Returns:
        list: A list of the most common colors as RGB tuples, sorted by frequency.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
        
    # Load image and convert to RGB
    image = Image.open(image_path).convert('RGB')
    
    # Resize for performance, preserving aspect ratio
    image.thumbnail((100, 100))
    
    # Get pixel data as a NumPy array
    pixels = np.array(image)
    pixels = pixels.reshape(-1, 3)
    
    # If the image has few colors, no need for clustering
    unique_colors = np.unique(pixels, axis=0)
    if len(unique_colors) <= num_colors:
        return [tuple(color) for color in unique_colors]

    # For images with many colors, use k-means to find dominant colors
    kmeans = KMeans(n_clusters=num_colors, random_state=0, n_init=10)
    kmeans.fit(pixels)
    
    # Get the RGB values of the cluster centers
    colors = kmeans.cluster_centers_.astype(int)
    
    # Sort colors by frequency to present the most common ones first
    labels = kmeans.labels_
    counts = np.bincount(labels, minlength=num_colors)
    sorted_indices = np.argsort(-counts)
    
    sorted_colors = colors[sorted_indices]
    
    return [tuple(color) for color in sorted_colors]

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