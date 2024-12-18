from dotenv import load_dotenv
import os

load_dotenv()

print("OpenAI API Key:", os.getenv("OPENAI_API_KEY", "Not found"))
print("GitHub Token:", os.getenv("GITHUB_TOKEN", "Not found"))
print("Capacities API Key:", os.getenv("CAPACITIES_API_KEY", "Not found"))
print("Capacities Space ID:", os.getenv("CAPACITIES_SPACE_ID", "Not found"))
print("YouTube API Key:", os.getenv("YOUTUBE_API_KEY", "Not found"))
