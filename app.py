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

# Load environment variables
load_dotenv()

# Verify API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")

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

def display_results(results, capacities_handler):
    """Display analysis results"""
    # Initialize states in session_state if they don't exist
    if 'results' not in st.session_state:
        st.session_state.results = results
    if 'weblink_status' not in st.session_state:
        st.session_state.weblink_status = None
    if 'weblink_url' not in st.session_state:
        st.session_state.weblink_url = None
    
    st.success("Analysis completed successfully!")
    
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
    with st.expander("Complete Transcript"):
        st.write(results["transcript"])
    
    # Processing date
    if "processed_date" in results:
        st.caption(f"Processed on: {results['processed_date']}")

async def main():
    st.title("URL Content Analyzer")
    st.markdown("Analyze YouTube videos or GitHub repositories")
    
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
        if is_youtube_url(url):
            # YouTube video processing
            st.subheader("Processing YouTube Video")
            language = st.selectbox("Select language:", ["en", "es"])
            
            if st.button("Analyze Video"):
                try:
                    results = await process_video(url, language, processor)
                    if results:
                        display_results(results, capacities_handler)
                except Exception as e:
                    st.error(f"Error processing video: {str(e)}")
                    
        elif is_github_url(url):
            # GitHub repository processing
            st.subheader("Processing GitHub Repository")
            owner, repo = extract_github_info(url)
            
            if owner and repo:
                if st.button("Analyze Repository"):
                    try:
                        github_token = os.getenv('GITHUB_TOKEN')
                        if not github_token:
                            st.error("GitHub token not found in environment variables.")
                            return
                            
                        analyzer = GitHubRepoAnalyzer(owner, repo, github_token)
                        analysis = analyzer.analyze_repo()
                        
                        if analysis["readme"]:
                            st.markdown("### README Content")
                            st.markdown(analysis["readme"])
                            
                            # Generate and display tags
                            tags = generate_tags(analysis["readme"])
                            if tags:
                                st.markdown("### Generated Tags")
                                st.write(", ".join(tags))
                            
                            # Create WebLink in Capacities
                            capacities_api_key = os.getenv('CAPACITIES_API_KEY')
                            space_id = os.getenv('SPACE_ID')
                            
                            if capacities_api_key and space_id:
                                try:
                                    headers = {
                                        "Authorization": f"Bearer {capacities_api_key}",
                                        "Content-Type": "application/json",
                                        "accept": "application/json"
                                    }
                                    
                                    data = {
                                        "spaceId": space_id,
                                        "url": url,
                                        "titleOverwrite": f"{owner}/{repo} README",
                                        "descriptionOverwrite": "GitHub README.md",
                                        "mdText": analysis["readme"]
                                    }
                                    
                                    response = requests.post(
                                        "https://api.capacities.io/save-weblink",
                                        headers=headers,
                                        json=data
                                    )
                                    
                                    if response.status_code == 200:
                                        st.success("Successfully saved to Capacities!")
                                    else:
                                        st.error("Failed to save to Capacities")
                                except Exception as e:
                                    st.error(f"Error saving to Capacities: {str(e)}")
                        else:
                            st.error("README not found in the repository")
                    except Exception as e:
                        st.error(f"Error analyzing repository: {str(e)}")
            else:
                st.error("Invalid GitHub repository URL")
        else:
            st.error("Please enter a valid YouTube video or GitHub repository URL")

if __name__ == "__main__":
    asyncio.run(main())