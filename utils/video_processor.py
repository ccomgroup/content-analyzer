import yt_dlp
import os
import tempfile
import openai
import subprocess
from pydub import AudioSegment
import math
import asyncio
import concurrent.futures
from youtube_transcript_api import YouTubeTranscriptApi
import re

class VideoProcessor:
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("No API key provided")
        
        self.api_key = api_key
        self.client = openai.Client(api_key=api_key)
        self.ffmpeg_path = self._get_ffmpeg_path()

    def _get_ffmpeg_path(self):
        """Get the ffmpeg path"""
        try:
            # First try with which/where
            result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            
            # Common paths on macOS
            common_paths = [
                '/opt/homebrew/bin/ffmpeg',
                '/usr/local/bin/ffmpeg',
                '/usr/bin/ffmpeg'
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    return path
            
            return None
        except Exception:
            return None

    def _get_video_id(self, url):
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    async def get_transcript(self, url):
        """Get video transcript from YouTube"""
        video_id = self._get_video_id(url)
        if not video_id:
            raise ValueError("Could not get video ID")

        try:
            transcript_list = await asyncio.to_thread(
                YouTubeTranscriptApi.get_transcript,
                video_id,
                languages=['en', 'es']
            )
            
            # Join all texts with timestamps
            full_transcript = ""
            timestamps = []
            
            for entry in transcript_list:
                timestamp = int(entry['start'])
                text = entry['text']
                timestamps.append({
                    'time': self._format_timestamp(timestamp),
                    'text': text
                })
                full_transcript += f" {text}"
            
            return full_transcript.strip(), timestamps
            
        except Exception:
            return None, None

    def _format_timestamp(self, seconds):
        """Convert seconds to HH:MM:SS format"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    async def process_content(self, transcript, timestamps=None):
        """Process video content to generate chapters, summary, and tags"""
        tasks = []
        
        # Create tasks for parallel processing
        tasks.append(self._generate_chapters(transcript, timestamps))
        tasks.append(self._generate_tags(transcript))
        tasks.append(self._generate_summary(transcript))
        
        # Execute tasks in parallel
        results = await asyncio.gather(*tasks)
        
        return {
            "chapters": results[0],
            "tags": results[1],
            "summary": results[2]
        }

    async def _generate_chapters(self, transcript, timestamps=None):
        """Generate video chapters with summaries"""
        if timestamps:
            # Use existing timestamps to generate chapters
            chapter_points = []
            current_chapter = {"text": "", "start": timestamps[0]['time']}
            
            for i, entry in enumerate(timestamps):
                current_chapter["text"] += f" {entry['text']}"
                
                # Create new chapter every ~5 minutes
                if i > 0 and i % 30 == 0:
                    chapter_points.append(current_chapter)
                    current_chapter = {"text": "", "start": entry['time']}
            
            # Add the last chapter
            if current_chapter["text"]:
                chapter_points.append(current_chapter)
                
            # Generate summaries for each chapter
            chapters = []
            for chapter in chapter_points:
                summary = await self._summarize_text(chapter["text"])
                chapters.append({
                    "timestamp": chapter["start"],
                    "title": summary[:50] + "...",
                    "summary": summary
                })
            
            return {"chapters": chapters}
        else:
            # Fallback to previous method if no timestamps
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Generate concise and relevant chapters."},
                    {"role": "user", "content": f"Generate 3-5 chapters with timestamps for:\n\n{transcript[:4000]}"}
                ]
            )
            return {"chapters": [{"timestamp": "00:00", "title": "Start", "summary": response.choices[0].message.content}]}

    async def _generate_tags(self, transcript):
        """Generate relevant tags"""
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Generate 5-8 relevant and concise tags."},
                {"role": "user", "content": f"Generate tags for:\n\n{transcript[:2000]}"}
            ]
        )
        tags = response.choices[0].message.content.split(',')
        return [tag.strip().replace('#', '') for tag in tags]

    async def _generate_summary(self, transcript):
        """Generate a summary of the content"""
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Generate a concise summary."},
                {"role": "user", "content": f"Summarize this content in 2-3 paragraphs:\n\n{transcript[:4000]}"}
            ]
        )
        return response.choices[0].message.content

    async def _summarize_text(self, text):
        """Generate a short summary of a text"""
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Generate a very concise summary."},
                {"role": "user", "content": f"Summarize this in one sentence:\n\n{text[:1000]}"}
            ]
        )
        return response.choices[0].message.content

    def get_video_info(self, url):
        """Get basic video information"""
        if not url:
            raise ValueError("Video URL not provided")
        
        # Validate URL format
        video_id = self._get_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,  # Changed to False to get more information
                'format': 'best',       # Specify format
                'ignoreerrors': False   # Do not ignore errors
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # Try to extract information
                    info = ydl.extract_info(url, download=False)
                    
                    if not info:
                        raise Exception("Could not get video information")
                    
                    # Print debug information
                    print(f"Debug - Video ID: {video_id}")
                    print(f"Debug - Info keys: {info.keys()}")
                    
                    return {
                        "title": info.get('title', 'Unknown Title'),
                        "author": info.get('uploader', 'Unknown Author'),
                        "views": info.get('view_count', 0),
                        "length": info.get('duration', 0),
                        "publish_date": info.get('upload_date', 'Unknown Date'),
                        "thumbnail_url": info.get('thumbnail', ''),
                        "captions_available": bool(info.get('subtitles', {}))
                    }
                except Exception as e:
                    print(f"Debug - Error in extract_info: {str(e)}")
                    raise
                
        except Exception as e:
            print(f"Debug - General error: {str(e)}")
            raise Exception(f"Error getting video information: {str(e)}")

    def download_audio(self, url):
        """Download video audio"""
        try:
            temp_dir = tempfile.gettempdir()
            output_file = os.path.join(temp_dir, 'audio.mp3')
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'outtmpl': output_file,
                'ffmpeg_location': self.ffmpeg_path,
                'quiet': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if not os.path.exists(output_file):
                raise Exception("Could not generate audio file")
                
            return output_file
        except Exception as e:
            raise Exception(f"Error downloading audio: {str(e)}")

    def transcribe_audio(self, audio_path, language):
        """Transcribe audio using OpenAI Whisper"""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        try:
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language
                )
            return response.text
        except Exception as e:
            raise Exception(f"Error transcribing audio: {str(e)}")