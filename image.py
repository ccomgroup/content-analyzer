from openai import OpenAI
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Function to generate an AI image based on a prompt
def generate_ai_image(prompt, cache_dir='.cache', image_name='ai_generated_image.png'):
    try:
        # Create an image generation request using the new API
        response = client.images.generate(
            model="dall-e-2",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )

        # Get the image URL from the response
        image_url = response.data[0].url

        # Ensure the cache directory exists
        os.makedirs(cache_dir, exist_ok=True)

        # Define the path to save the image
        image_path = os.path.join(cache_dir, image_name)

        # Download and save the image
        image_response = requests.get(image_url)
        with open(image_path, 'wb') as f:
            f.write(image_response.content)

        print(f"Image generated and saved to {image_path}")
        return image_path
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        return None
