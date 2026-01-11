"""
Generate Placeholder Slides
Creates 1920x1080 placeholder images with text for testing.
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

def create_slides(output_dir, count=14):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Try to load a font, fallback to default
    try:
        # MacOS usually has Arial or Helvetica
        font = ImageFont.truetype("Arial.ttf", 100)
    except IOError:
        font = ImageFont.load_default()

    for i in range(1, count + 1):
        filename = f"slide_{i:03d}.png"
        path = os.path.join(output_dir, filename)
        
        # Create image
        img = Image.new('RGB', (1920, 1080), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        
        # Draw text
        text = f"Slide {i:03d}"
        
        # Rough centering
        # textbox = d.textbbox((0, 0), text, font=font)
        # text_w = textbox[2] - textbox[0]
        # text_h = textbox[3] - textbox[1]
        
        d.text((800, 500), text, fill=(255, 255, 255), font=font)
        
        img.save(path)
        print(f"Created {path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        out_dir = sys.argv[1]
    else:
        out_dir = "assets_sample_1/images"
        
    create_slides(out_dir)
