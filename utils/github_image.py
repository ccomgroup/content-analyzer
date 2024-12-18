import numpy as np
from PIL import Image, ImageDraw
import random

def create_abstract_image(size=(800, 400)):
    """
    Creates an abstract geometric image for GitHub repositories.
    No text is included in the image.
    """
    # Create a new image with a dark background
    image = Image.new('RGB', size, (30, 33, 36))
    draw = ImageDraw.Draw(image)
    
    # Generate a color palette
    colors = [
        (66, 134, 244),   # Blue
        (52, 168, 83),    # Green
        (251, 188, 4),    # Yellow
        (234, 67, 53),    # Red
        (255, 255, 255),  # White
    ]
    
    # Draw multiple geometric shapes
    for _ in range(15):
        shape_type = random.choice(['circle', 'rectangle', 'line'])
        color = random.choice(colors)
        
        x = random.randint(0, size[0])
        y = random.randint(0, size[1])
        
        if shape_type == 'circle':
            radius = random.randint(20, 100)
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                        fill=None, outline=color, width=3)
        
        elif shape_type == 'rectangle':
            width = random.randint(40, 200)
            height = random.randint(40, 100)
            draw.rectangle([x, y, x+width, y+height], 
                         fill=None, outline=color, width=3)
        
        else:  # line
            end_x = x + random.randint(-200, 200)
            end_y = y + random.randint(-100, 100)
            draw.line([x, y, end_x, end_y], fill=color, width=3)
    
    # Add connecting lines in background
    for _ in range(10):
        start = (random.randint(0, size[0]), random.randint(0, size[1]))
        end = (random.randint(0, size[0]), random.randint(0, size[1]))
        draw.line([start, end], fill=(50, 50, 50), width=1)
    
    return image

def save_abstract_image(output_path):
    """
    Creates and saves an abstract image for GitHub repositories
    """
    image = create_abstract_image()
    image.save(output_path, 'PNG')
    return output_path
