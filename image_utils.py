"""
Utility functions for image processing operations.
Centralizes image splitting and other image-related functionality.
"""
import os
from PIL import Image
from config import CHUNK_SIZE
import numpy as np
from sklearn.cluster import KMeans
from skimage.color import rgb2lab, lab2rgb
from collections import defaultdict


def extract_and_group_colors_kmeans(image_path, num_colors=10):
    """
    Extracts and groups colors from an image using K-means clustering
    in the CIELAB color space for perceptually accurate results.

    Args:
        image_path (str): Path to the source image.
        num_colors (int): The target number of color groups to create.

    Returns:
        dict: A dictionary where keys are group names (e.g., "Group 1")
              and values are lists of the original RGB colors belonging to that group.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Load image and convert to RGB
    image = Image.open(image_path).convert('RGB')
    image.thumbnail((150, 150)) # Resize for performance

    # Get pixel data and convert to a list of colors
    pixels = np.array(image)
    pixels = pixels.reshape(-1, 3)

    # Convert RGB pixel data to LAB color space for clustering
    # We normalize RGB values to be between 0 and 1 for the conversion
    lab_pixels = rgb2lab(pixels / 255.0)

    # Perform K-means clustering
    # n_init='auto' is recommended to avoid a FutureWarning
    kmeans = KMeans(n_clusters=num_colors, n_init='auto', random_state=42)
    kmeans.fit(lab_pixels)

    # Group original RGB pixels based on the cluster labels
    grouped_colors = defaultdict(list)
    for i, label in enumerate(kmeans.labels_):
        original_rgb_color = tuple(pixels[i])
        grouped_colors[f"Group {label + 1}"].append(original_rgb_color)

    # For display, we can also find the average color of each group
    # The cluster centers are in LAB, so convert them back to RGB
    center_rgb_lab = lab2rgb(kmeans.cluster_centers_.reshape(num_colors, 1, 3))
    center_rgb = (center_rgb_lab * 255).astype(int)

    # You could optionally return these average colors to name the groups
    # For now, we'll just return the grouped original colors.

    # Remove duplicates from each group list
    for group in grouped_colors:
        grouped_colors[group] = sorted(list(set(grouped_colors[group])), key=lambda c: sum(int(x) for x in c))

    return grouped_colors

def colors_are_similar(color1, color2, tolerance=0):
    """
    Checks if two RGB colors are similar within a given tolerance.
    (This function should already be in your file and is correct)
    """
    if tolerance == 0:
        return color1 == color2
        
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    
    # Ensure color components are integers for the calculation
    return (abs(int(r1) - int(r2)) <= tolerance and
            abs(int(g1) - int(g2)) <= tolerance and
            abs(int(b1) - int(b2)) <= tolerance)

def extract_common_colors(image_path, num_colors=5, tolerance=25):
    """
    Extracts the most visually distinct common colors from an image.

    It works by first finding the most frequent colors, then iterating through
    them and only adding a color to the final list if it's not visually
    similar (within a given tolerance) to a color already selected.

    Args:
        image_path (str): Path to the source image.
        num_colors (int): The target number of distinct colors to return.
        tolerance (int): The tolerance for grouping similar colors. A higher
                         value means more shades will be considered the same.

    Returns:
        list: A list of the most common, visually distinct colors as RGB tuples.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Load image and convert to RGB
    image = Image.open(image_path).convert('RGB')

    # Resize for performance
    image.thumbnail((150, 150))

    # Get pixel data and find unique colors sorted by frequency
    pixels = np.array(image)
    pixels = pixels.reshape(-1, 3)
    unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
    
    # Create a list of all unique colors, sorted by frequency
    sorted_indices = np.argsort(-counts)
    frequent_colors = [tuple(c) for c in unique_colors[sorted_indices]]

    # --- New Logic to find DISTINCT colors ---
    distinct_colors = []
    if not frequent_colors:
        return []

    # Always add the single most frequent color to start our list
    distinct_colors.append(frequent_colors[0])

    # Iterate through the rest of the frequent colors
    for color in frequent_colors[1:]:
        # Stop when we have found enough distinct colors
        if len(distinct_colors) >= num_colors:
            break

        # Check if this color is similar to any color we've already selected
        is_similar_to_an_existing_color = False
        for selected_color in distinct_colors:
            if colors_are_similar(color, selected_color, tolerance):
                is_similar_to_an_existing_color = True
                break # It's similar, no need to check the others

        # If it's not similar to any of our chosen colors, it's a new distinct color
        if not is_similar_to_an_existing_color:
            distinct_colors.append(color)

    return distinct_colors

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