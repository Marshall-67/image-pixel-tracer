from PIL import Image
import os
import sys

def split_image(input_path, output_dir, chunk_size=32):
    """
    Splits an image into 32x32 chunks and saves them as separate PNG files.

    Args:
        input_path (str): Path to the input image.
        output_dir (str): Directory to save the output chunks.
        chunk_size (int): Size of each chunk (default: 32).
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load the image
    img = Image.open(input_path)
    width, height = img.size

    # Calculate number of chunks
    num_chunks_x = (width + chunk_size - 1) // chunk_size
    num_chunks_y = (height + chunk_size - 1) // chunk_size

    for i in range(num_chunks_y):
        for j in range(num_chunks_x):
            # Calculate crop box
            left = j * chunk_size
            upper = i * chunk_size
            right = min(left + chunk_size, width)
            lower = min(upper + chunk_size, height)

            # Crop the chunk
            chunk = img.crop((left, upper, right, lower))

            # If the chunk is smaller than chunk_size, pad it
            if chunk.width < chunk_size or chunk.height < chunk_size:
                padded_chunk = Image.new(
                    img.mode,
                    (chunk_size, chunk_size),
                    (0, 0, 0, 0) if img.mode == 'RGBA' else (0, 0, 0)
                )
                padded_chunk.paste(chunk, (0, 0))
                chunk = padded_chunk

            # Save the chunk
            chunk_filename = f"chunk_{i}_{j}.png"
            chunk_path = os.path.join(output_dir, chunk_filename)
            chunk.save(chunk_path)
            print(f"Saved chunk: {chunk_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py <input_image> <output_dir>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    split_image(input_path, output_dir)