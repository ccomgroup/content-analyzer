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

# Verify API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")

github_token = os.getenv("GITHUB_TOKEN")
if not github_token:
    raise ValueError("GITHUB_TOKEN not found in .env file")

print(f"API key loaded: {api_key[:8]}...")  # Debug only

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
    cache_manager = CacheManager()
    
    # Check cache
    cached_result = cache_manager.get_cached_result(url)
    if cached_result:
        st.success("Results found in cache!")
        return cached_result
    
    progress_text = "Operation in progress. Please wait..."
    my_bar = st.progress(0, text=progress_text)
    
    try:
        with st.status("Processing video...", expanded=True) as status:
            # Get video information
            status.write("Getting video information...")
            video_info = processor.get_video_info(url)
            my_bar.progress(20, text="Video information obtained")
            
            # Show preliminary information
            st.write(f"Processing: {video_info['title']}")
            st.write(f"Channel: {video_info['author']}")
            
            # Try to get YouTube transcript
            status.write("Getting transcript...")
            transcript, timestamps = await processor.get_transcript(url)
            
            if not transcript:
                status.write("Downloading and transcribing audio...")
                # Use previous transcription method
                audio_path = processor.download_audio(url)
                transcript = processor.transcribe_audio(audio_path, language)
                timestamps = None
                os.remove(audio_path)
            
            my_bar.progress(60, text="Transcription completed")
            
            # Process content in parallel
            status.write("Analyzing content...")
            content_results = await processor.process_content(transcript, timestamps)
            my_bar.progress(90, text="Analysis completed")
            
            result = {
                "info": video_info,
                "transcript": transcript,
                "chapters": content_results["chapters"],
                "tags": content_results["tags"],
                "summary": content_results["summary"],
                "video_url": url,
                "processed_date": datetime.now().isoformat()
            }
            
            # Save to cache
            cache_manager.save_to_cache(url, result)
            my_bar.progress(100, text="Process completed!")
            
            return result
            
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
        
        # Format results
        results = {
            'type': 'github',
            'info': {
                'owner': owner,
                'repo': repo,
                'url': url,
                'title': f"{owner}/{repo} README"
            },
            'readme': readme_content,
            'processed_date': datetime.now().isoformat()
        }
        
        return results
    except Exception as e:
        if "rate limit exceeded" in str(e).lower():
            raise Exception("OpenAI API rate limit exceeded. Please try again in about an hour.")
        raise Exception(f"Error analyzing repository: {str(e)}")

def display_results(results, capacities_handler):
    """Display analysis results"""
    if results['type'] == 'github':
        # Display README
        st.subheader("Repository README")
        
        # Clean up HTML tags and convert to markdown
        readme_content = results['readme']
        # Remove HTML image tags and badges
        readme_content = re.sub(r'<img[^>]*>', '', readme_content)
        # Remove other HTML tags but keep their content
        readme_content = re.sub(r'<[^>]+>', '', readme_content)
        # Remove empty lines created by HTML removal
        readme_content = '\n'.join(line for line in readme_content.split('\n') if line.strip())
        
        st.markdown(readme_content)
        
        # Capacities export section
        st.subheader("Export to Capacities")
        
        if st.button("Export to Capacities"):
            try:
                # Update the README content in results before sending to Capacities
                results['readme'] = readme_content
                weblink = capacities_handler.create_weblink(results)
                
                if weblink:
                    st.success("Successfully exported to Capacities!")
                    st.write(f"Processed on: {results['processed_date']}")
            except Exception as e:
                st.error(f"Error exporting to Capacities: {str(e)}")
    
    elif results['type'] == 'youtube':
        # Video information
        st.header("Analysis Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(results["info"]["thumbnail_url"], caption="Video thumbnail")
        
        with col2:
            st.subheader("Video Information")
            st.write(f"**Title:** {results['info']['title']}")
            st.write(f"**Channel:** {results['info']['author']}")
            st.write(f"**Views:** {results['info']['views']:,}")
            st.write(f"**Duration:** {results['info']['length']} seconds")
            st.write(f"**Publication Date:** {results['info']['publish_date']}")
        
        # Summary
        if "summary" in results:
            st.subheader("Video Summary")
            st.write(results["summary"])
        
        # Chapters
        st.subheader("Video Chapters")
        for chapter in results["chapters"]["chapters"]:
            with st.expander(f"{chapter['timestamp']} - {chapter['title']}"):
                st.write(chapter["summary"])
        
        # Tags
        st.subheader("Generated Tags")
        st.write(" ".join([f"#{tag}" for tag in results["tags"]]))
        
        # Capacities section
        st.subheader("Export to Capacities")
        
        # Columns for button and status
        col1, col2 = st.columns([1, 2])
        
        def create_weblink():
            """Function to create weblink and update status"""
            try:
                with st.spinner("Creating Weblink in Capacities..."):
                    weblink = capacities_handler.create_weblink(st.session_state.results)
                    st.session_state.weblink_status = "success"
                    st.session_state.weblink_url = weblink['url']
            except Exception as e:
                st.session_state.weblink_status = "error"
                st.session_state.weblink_error = str(e)
        
        with col1:
            # Only show button if no weblink has been successfully created
            if st.session_state.weblink_status != "success":
                st.button(
                    "Create Weblink",
                    on_click=create_weblink,
                    key="create_weblink_button"
                )
        
        with col2:
            # Show status or result as appropriate
            if st.session_state.weblink_status == "success":
                st.success("Weblink created successfully!")
                st.markdown(f"[View in Capacities]({st.session_state.weblink_url})")
            elif st.session_state.weblink_status == "error":
                st.error(f"Error creating Weblink: {st.session_state.weblink_error}")
        
        # Transcript and other details
        if 'transcript' in results:
            with st.expander("Complete Transcript"):
                st.write(results["transcript"])
        
        # Processing date
        if "processed_date" in results:
            st.caption(f"Processed on: {results['processed_date']}")

async def main():
    st.title("URL Content Analyzer")
    st.write("Analyze YouTube videos or GitHub repositories")
    
    # Initialize handlers
    api_key = os.getenv("OPENAI_API_KEY")
    capacities_api_key = os.getenv("CAPACITIES_API_KEY")
    
    if not api_key:
        st.error("OpenAI API key not found in environment variables.")
        return
        
    if not capacities_api_key:
        st.error("Capacities API key not found in environment variables.")
        return
        
    processor = VideoProcessor(api_key=api_key)
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