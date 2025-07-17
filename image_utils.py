"""
Utility functions for image processing operations.
Centralizes image splitting and other image-related functionality.
"""
import os
from PIL import Image
from config import CHUNK_SIZE
import numpy as np
# Import DBSCAN and remove KMeans
from sklearn.cluster import DBSCAN
from skimage.color import rgb2lab, lab2rgb
from collections import defaultdict


def extract_color_groups(image_path, eps: float = 10.0, min_samples_pct=0.05):
    """
    Extracts and groups perceptually similar colors from an image using DBSCAN
    clustering in the CIELAB color space.

    This method is effective at finding distinct color families without
    specifying the number of groups in advance.

    Args:
        image_path (str): Path to the source image.
        eps (float): The maximum distance (in LAB space) between two samples
                     for one to be considered as in the neighborhood of the other.
                     Lower values result in more, tighter color groups.
        min_samples_pct (float): The percentage of total pixels required to form a
                                 dense region (a color group).

    Returns:
        dict: A dictionary where keys are group names (e.g., "Group 1 (RGB: 255,0,0)")
              and values are lists of the original RGB colors in that group.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Load image, resize for performance, and convert to RGB
    image = Image.open(image_path).convert('RGB')
    image.thumbnail((150, 150))

    # Get pixel data as a NumPy array
    pixels = np.array(image)
    pixels = pixels.reshape(-1, 3)

    # Avoid clustering if the image is tiny or has few colors
    if len(pixels) < 50:
        unique_colors = list(set(map(tuple, pixels)))
        return {"Group 1": unique_colors}

    # Convert RGB pixel data to LAB color space for perceptually uniform clustering
    # Normalize RGB values to be between 0 and 1 for the conversion
    lab_pixels = rgb2lab(pixels / 255.0)

    # Calculate min_samples based on a percentage of the total pixels
    # This makes the clustering more robust to different image sizes
    min_samples = max(5, int(len(pixels) * (min_samples_pct / 100.0)))

    # Perform DBSCAN clustering. n_jobs=-1 uses all available CPU cores.
    db = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean', n_jobs=-1).fit(lab_pixels)
    
    # Get the set of unique labels (each unique label is a cluster)
    unique_labels = set(db.labels_)
    
    # --- Group original RGB pixels based on the cluster labels ---
    grouped_colors = defaultdict(list)
    # The label -1 is for "noise" points that don't belong to any cluster
    noise_colors = []

    for i, label in enumerate(db.labels_):
        original_rgb_color = tuple(pixels[i])
        if label == -1:
            noise_colors.append(original_rgb_color)
        else:
            grouped_colors[label].append(original_rgb_color)
    
    # --- Process the found clusters ---
    final_groups = {}
    
    # Sort clusters by size (number of pixels) to give them stable names
    sorted_labels = sorted(grouped_colors.keys(), key=lambda k: len(grouped_colors[k]), reverse=True)
    
    group_counter = 1
    for label in sorted_labels:
        cluster_pixels = grouped_colors[label]
        
        # Calculate the average color of the group to create a representative name
        # We average the LAB values and convert back to RGB for accuracy
        lab_cluster_pixels = rgb2lab(np.array(cluster_pixels) / 255.0)
        avg_lab_color = np.mean(lab_cluster_pixels, axis=0)
        # Reshape for lab2rgb and convert back
        avg_rgb_color_float = lab2rgb(avg_lab_color.reshape(1, 1, 3))
        avg_rgb_color = (avg_rgb_color_float[0][0] * 255).astype(int)
        r, g, b = avg_rgb_color
        
        # Create a descriptive group name and store the unique colors
        group_name = f"Group {group_counter} (RGB: {r},{g},{b})"
        unique_colors_in_group = sorted(list(set(cluster_pixels)), key=lambda c: sum(int(x) for x in c))
        final_groups[group_name] = unique_colors_in_group
        group_counter += 1
        
    # Add the "noise" pixels as their own group if they exist
    if noise_colors:
        unique_noise_colors = sorted(list(set(noise_colors)), key=lambda c: sum(int(x) for x in c))
        final_groups["Other Colors"] = unique_noise_colors

    return final_groups

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