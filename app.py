from image import generate_ai_image
import streamlit as st
import openai
import os
from dotenv import load_dotenv
import tempfile
from utils.video_processor import VideoProcessor
from utils.capacities_handler import CapacitiesHandler
import yt_dlp
import time
from utils.cache_manager import CacheManager
import asyncio
from datetime import datetime
import requests
from github_repo_analyzer.analyzer import GitHubRepoAnalyzer
import re

# Load environment variables
load_dotenv()

# Verify API keys
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")

github_token = os.getenv("GITHUB_TOKEN")
if not github_token:
    raise ValueError("GITHUB_TOKEN not found in .env file")

print(f"API key loaded: {api_key[:8]}...")  # Debug only

# Initialize session state variables
if 'weblink_status' not in st.session_state:
    st.session_state.weblink_status = None
if 'weblink_url' not in st.session_state:
    st.session_state.weblink_url = None
if 'weblink_error' not in st.session_state:
    st.session_state.weblink_error = None
if 'results' not in st.session_state:
    st.session_state.results = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = os.getenv("OPENAI_API_KEY", "")
if 'model_type' not in st.session_state:
    st.session_state.model_type = "openai"
if 'ollama_model' not in st.session_state:
    st.session_state.ollama_model = "llama2"

# Initialize session state for shutdown handling
if 'should_shutdown' not in st.session_state:
    st.session_state.should_shutdown = False

# Configure dark theme
st.set_page_config(
    page_title="URL Content Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.google.com',
        'Report a bug': "https://www.github.com",
        'About': "# URL Content Analyzer - YouTube & GitHub"
    }
)

# Apply custom dark theme
st.markdown("""
    <style>
        .stApp {
            background-color: #1E1E1E;
            color: #FFFFFF;
        }
        .stTextInput > div > div > input {
            background-color: #2D2D2D;
            color: #FFFFFF;
        }
        .stSelectbox > div > div > select {
            background-color: #D2D2D2;
            color: #FFFFFF;
        }
    </style>
""", unsafe_allow_html=True)

def is_youtube_url(url: str) -> bool:
    """Check if the URL is a YouTube URL"""
    youtube_patterns = [
        'youtube.com/watch',
        'youtu.be/',
        'youtube.com/shorts/'
    ]
    return any(pattern in url.lower() for pattern in youtube_patterns)

def is_github_url(url: str) -> bool:
    """Check if the URL is a GitHub repository URL"""
    return 'github.com/' in url.lower()

def extract_github_info(url: str) -> tuple:
    """Extract owner and repo from GitHub URL"""
    parts = url.rstrip('/').split('/')
    if len(parts) >= 5:  # https://github.com/owner/repo
        return parts[-2], parts[-1]
    return None, None

async def process_video(url, language, processor):
    """Process the complete video and return results"""
    try:
        # Create a progress bar
        my_bar = st.progress(0, text="Starting video processing...")
        
        # Step 1: Extract video information (20%)
        my_bar.progress(20, text="Extracting video information...")
        info = processor.get_video_info(url)
        if not info:
            raise Exception("Failed to extract video information")
        
        # Step 2: Get video transcript (40%)
        my_bar.progress(40, text="Getting video transcript...")
        transcript, timestamps = await processor.get_transcript(url, language)
        if not transcript:
            raise Exception("Failed to get video transcript")
        
        # Step 3: Process transcript (70%)
        my_bar.progress(70, text="Processing transcript...")
        content = await processor.process_content(transcript, timestamps)
        if not content:
            raise Exception("Failed to process transcript")
        
        # Step 4: Format results (100%)
        my_bar.progress(100, text="Formatting results...")
        results = {
            'type': 'youtube',
            'url': url,
            'title': info.get('title', ''),
            'author': info.get('author', ''),
            'views': info.get('views', 0),
            'length': info.get('length', 0),
            'publish_date': info.get('publish_date', ''),
            'thumbnail_url': info.get('thumbnail_url', ''),
            'summary': content.get('summary', ''),
            'chapters': content.get('chapters', []),
            'tags': content.get('tags', []),
            'transcript': transcript,
            'processed_date': datetime.now().isoformat()
        }
        
        my_bar.empty()
        return results
        
    except Exception as e:
        my_bar.empty()
        raise e

async def process_github_repo(url: str) -> dict:
    """Process GitHub repository README and return analysis results"""
    try:
        owner, repo = extract_github_info(url)
        analyzer = GitHubRepoAnalyzer(owner, repo, github_token)
        
        # Get only README content
        readme_content = analyzer.get_readme()
        if not readme_content:
            raise Exception("README not found in the repository")
        
        # Generate abstract art for the repository
        image_prompt = (
            "Create an abstract digital artwork merging Van Gogh and Pollock styles. "
            "Use dynamic swirling patterns, energetic splashes, and bold color harmonies. "
            "Make it purely abstract - NO text, NO symbols, NO literal representations. "
            "Style: Modern, expressive, with rich textures and emotional depth. "
            f"Let the energy reflect the essence of code and creativity."
        )
        image_path = generate_ai_image(image_prompt, image_name=f"{owner}_{repo}_image.png")
        
        # Format results
        results = {
            'type': 'github',
            'repo_name': f"{owner}/{repo}",
            'url': url,  # Set the original URL
            'summary': readme_content[:1000],  # Limit summary to 1000 chars
            'full_content': readme_content,
            'image_path': image_path,
            'processed_date': datetime.now().isoformat()
        }
        
        return results
    except Exception as e:
        if "rate limit exceeded" in str(e).lower():
            raise Exception("OpenAI API rate limit exceeded. Please try again in about an hour.")
        raise Exception(f"Error analyzing repository: {str(e)}")

def display_results(results, capacities_handler):
    """Display analysis results"""
    # Store results in session state
    st.session_state.results = results
    
    if results['type'] == 'github':
        # Display repository name
        st.subheader(f"Repository: {results['repo_name']}")
        
        # Display README
        st.subheader("Repository README")
        
        # Clean up HTML tags and convert to markdown
        readme_content = results['full_content']
        # Remove HTML image tags and badges
        readme_content = re.sub(r'<img[^>]*>', '', readme_content)
        # Remove other HTML tags but keep their content
        readme_content = re.sub(r'<[^>]+>', '', readme_content)
        
        st.markdown(readme_content)
        
        # Display the generated image
        if results.get('image_path'):
            st.image(results['image_path'], caption="AI-generated visualization of the repository")
        
        # Export to Capacities
        try:
            capacities_response = capacities_handler.create_weblink(results)
            st.success("Successfully exported to Capacities!")
            st.json(capacities_response)
        except Exception as e:
            st.error(f"Error exporting to Capacities: {str(e)}")
            print(f"Error processing in Capacities: {str(e)}")
    
    elif results['type'] == 'youtube':
        # Video information
        st.header("Analysis Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(results["thumbnail_url"], caption="Video thumbnail")
        
        with col2:
            st.subheader("Video Information")
            st.write(f"**Title:** {results['title']}")
            st.write(f"**URL:** {results['url']}")
            st.write(f"**Author:** {results['author']}")
            st.write(f"**Views:** {results['views']}")
            st.write(f"**Length:** {results['length']}")
            st.write(f"**Publish Date:** {results['publish_date']}")
            st.write(f"**Summary:** {results['summary']}")
            st.write(f"**Tags:** {results['tags']}")
        
        # Transcript
        with st.expander("Complete Transcript"):
            st.write(results["transcript"])
        
        # Processing date
        if "processed_date" in results:
            st.caption(f"Processed on: {results['processed_date']}")
            
        # Export to Capacities
        try:
            capacities_response = capacities_handler.create_weblink(results)
            st.success("Successfully exported to Capacities!")
            st.json(capacities_response)
        except Exception as e:
            st.error(f"Error exporting to Capacities: {str(e)}")
            print(f"Error processing in Capacities: {str(e)}")

async def main():
    st.title("URL Content Analyzer")
    st.write("Analyze YouTube videos or GitHub repositories")
    
    # Sidebar configuration
    with st.sidebar:
        st.title("Settings")
        
        # Model Selection
        st.session_state.model_type = st.radio(
            "Select Model Type",
            ["openai", "ollama"],
            index=0 if st.session_state.model_type == "openai" else 1
        )
        
        if st.session_state.model_type == "openai":
            api_key = st.text_input("OpenAI API Key", value=st.session_state.api_key, type="password")
            if api_key != st.session_state.api_key:
                st.session_state.api_key = api_key
                if api_key:
                    os.environ["OPENAI_API_KEY"] = api_key
                    st.success("API key updated!")
        else:
            st.session_state.ollama_model = st.selectbox(
                "Select Ollama Model",
                ["llama2", "codellama", "mistral"],
                index=["llama2", "codellama", "mistral"].index(st.session_state.ollama_model)
            )

        # Add a shutdown button in the sidebar
        if st.button("Shutdown Application"):
            st.session_state.should_shutdown = True
            st.success("Shutting down... You can close this window.")
            st.stop()

    # Initialize handlers
    api_key = st.session_state.api_key
    capacities_api_key = os.getenv("CAPACITIES_API_KEY")
    
    if not api_key:
        st.error("API key not found. Please enter your API key in the sidebar.")
        return
        
    if not capacities_api_key:
        st.error("Capacities API key not found in environment variables.")
        return
        
    processor = VideoProcessor(
        api_key=api_key,
        model_type=st.session_state.model_type,
        ollama_model=st.session_state.ollama_model
    )
    capacities_handler = CapacitiesHandler(api_key=capacities_api_key)
    
    # URL input
    url = st.text_input("Enter URL (YouTube video or GitHub repository):")
    
    if url:
        try:
            if is_youtube_url(url):
                st.write("Processing YouTube Video")
                results = await process_video(url, "en", processor)
            elif is_github_url(url):
                st.write("Processing GitHub Repository")
                results = await process_github_repo(url)
            else:
                st.error("Invalid URL. Please enter a valid YouTube video or GitHub repository URL.")
                return
            
            # Display results
            display_results(results, capacities_handler)
            
        except Exception as e:
            error_msg = str(e)
            if "rate limit exceeded" in error_msg.lower():
                st.error("⚠️ OpenAI API rate limit exceeded. Please try again in about an hour.")
                st.info("This error occurs when we've made too many requests to OpenAI's API. The limit will reset automatically after some time.")
            else:
                st.error(f"Error analyzing content: {error_msg}")

if __name__ == "__main__":
    asyncio.run(main())