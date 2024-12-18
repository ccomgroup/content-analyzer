import yt_dlp
import os
import tempfile
import openai
import subprocess
import requests
from pydub import AudioSegment
import math
import asyncio
import concurrent.futures
from youtube_transcript_api import YouTubeTranscriptApi
import re

class VideoProcessor:
    def __init__(self, api_key, model_type="openai", ollama_model="llama2"):
        if model_type not in ["openai", "ollama"]:
            raise ValueError("Invalid model type. Supported models are 'openai' and 'ollama'.")

        self.model_type = model_type
        self.ollama_model = ollama_model
        
        if model_type == "openai":
            if not api_key:
                raise ValueError("No OpenAI API key provided")
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

    async def get_transcript(self, url, language='en'):
        """Get video transcript from YouTube"""
        video_id = self._get_video_id(url)
        if not video_id:
            raise ValueError("Could not get video ID")

        try:
            transcript_list = await asyncio.to_thread(
                YouTubeTranscriptApi.get_transcript,
                video_id,
                languages=[language, 'en'] if language != 'en' else ['en']
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
        try:
            # Split transcript into chunks of roughly equal size if it's too long
            max_chunk_size = 4000
            transcript_chunks = []
            
            if len(transcript) > max_chunk_size:
                # Split into sentences to preserve context
                sentences = transcript.split('. ')
                current_chunk = []
                current_size = 0
                
                for sentence in sentences:
                    sentence_size = len(sentence)
                    if current_size + sentence_size > max_chunk_size and current_chunk:
                        transcript_chunks.append('. '.join(current_chunk) + '.')
                        current_chunk = [sentence]
                        current_size = sentence_size
                    else:
                        current_chunk.append(sentence)
                        current_size += sentence_size
                
                if current_chunk:
                    transcript_chunks.append('. '.join(current_chunk) + '.')
            else:
                transcript_chunks = [transcript]

            # Process each chunk
            all_chapters = []
            all_tags = set()
            summaries = []
            
            for chunk in transcript_chunks:
                # Create tasks for parallel processing of each chunk
                chunk_tasks = [
                    self._generate_chapters(chunk, timestamps if len(transcript_chunks) == 1 else None),
                    self._generate_tags(chunk),
                    self._generate_summary(chunk)
                ]
                
                # Execute chunk tasks in parallel
                chunk_results = await asyncio.gather(*chunk_tasks)
                
                # Combine results
                all_chapters.extend(chunk_results[0])
                all_tags.update([tag.strip() for tag in chunk_results[1]])
                summaries.append(chunk_results[2])
            
            # Generate final summary from all chunk summaries
            final_summary = await self._generate_summary('\n'.join(summaries)) if len(summaries) > 1 else summaries[0]
            
            return {
                "chapters": sorted(all_chapters, key=lambda x: x['timestamp']),
                "tags": list(all_tags)[:10],  # Limit to top 10 most relevant tags
                "summary": final_summary
            }
            
        except Exception as e:
            print(f"Error processing content: {str(e)}")
            return {
                "chapters": [{"timestamp": "00:00:00", "title": "Start", "summary": "Error processing chapters"}],
                "tags": [],
                "summary": "Error processing content"
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
            
            return chapters
        else:
            # Fallback to previous method if no timestamps
            if self.model_type == "openai":
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Generate concise and relevant chapters."},
                        {"role": "user", "content": f"Generate 3-5 chapters with timestamps for:\n\n{transcript[:4000]}"}
                    ]
                )
                return [{"timestamp": "00:00", "title": "Start", "summary": response.choices[0].message.content}]
            else:
                # Use Ollama API
                try:
                    response = requests.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": self.ollama_model,
                            "prompt": f"Generate 3-5 concise chapters with timestamps for this content:\n\n{transcript[:4000]}"
                        }
                    )
                    return [{"timestamp": "00:00", "title": "Start", "summary": response.json()["response"]}]
                except Exception as e:
                    print(f"Error with Ollama API: {str(e)}")
                    return [{"timestamp": "00:00", "title": "Start", "summary": "Error generating chapters"}]

    async def _generate_tags(self, transcript):
        """Generate relevant tags"""
        if self.model_type == "openai":
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Generate 5-8 relevant and concise tags."},
                    {"role": "user", "content": f"Generate tags for:\n\n{transcript[:2000]}"}
                ]
            )
            tags = response.choices[0].message.content.split(',')
        else:
            # Use Ollama API
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": f"Generate 5-8 relevant and concise tags (comma-separated) for this content:\n\n{transcript[:2000]}"
                    }
                )
                tags = response.json()["response"].split(',')
            except Exception as e:
                print(f"Error with Ollama API: {str(e)}")
                return []

        return [tag.strip().replace('#', '') for tag in tags]

    async def _generate_summary(self, transcript):
        """Generate a summary of the content"""
        if self.model_type == "openai":
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Generate a concise summary."},
                    {"role": "user", "content": f"Summarize this content in 2-3 paragraphs:\n\n{transcript[:4000]}"}
                ]
            )
            return response.choices[0].message.content
        else:
            # Use Ollama API
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": f"Generate a concise 2-3 paragraph summary of this content:\n\n{transcript[:4000]}"
                    }
                )
                return response.json()["response"]
            except Exception as e:
                print(f"Error with Ollama API: {str(e)}")
                return "Error generating summary"

    async def _summarize_text(self, text):
        """Generate a short summary of a text"""
        if self.model_type == "openai":
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Generate a very concise summary."},
                    {"role": "user", "content": f"Summarize this in one sentence:\n\n{text[:1000]}"}
                ]
            )
            return response.choices[0].message.content
        else:
            # Use Ollama API
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": f"Summarize this in one sentence:\n\n{text[:1000]}"
                    }
                )
                return response.json()["response"]
            except Exception as e:
                print(f"Error with Ollama API: {str(e)}")
                return "Error generating summary"

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
                'extract_flat': False,
                'format': 'best[height<=1080]',  # Limit to 1080p or lower to avoid format issues
                'ignoreerrors': True,
                'no_color': True,
                'extractor_args': {
                    'youtube': {
                        'skip': ['dash', 'hls'],  # Skip DASH and HLS formats
                    }
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # Try to extract information
                    print(f"Debug - Extracting info for video ID: {video_id}")
                    info = ydl.extract_info(url, download=False)
                    
                    if not info:
                        raise Exception("Could not get video information")
                    
                    # Print debug information
                    print(f"Debug - Info keys: {info.keys()}")
                    
                    # Get the best thumbnail URL
                    thumbnails = info.get('thumbnails', [])
                    thumbnail_url = ''
                    if thumbnails:
                        # Sort thumbnails by resolution and pick the highest quality
                        sorted_thumbnails = sorted(
                            thumbnails,
                            key=lambda x: (x.get('height', 0) * x.get('width', 0)),
                            reverse=True
                        )
                        thumbnail_url = sorted_thumbnails[0].get('url', '')
                    
                    return {
                        "title": info.get('title', 'Unknown Title'),
                        "author": info.get('uploader', 'Unknown Author'),
                        "views": info.get('view_count', 0),
                        "length": info.get('duration', 0),
                        "publish_date": info.get('upload_date', 'Unknown Date'),
                        "thumbnail_url": thumbnail_url or info.get('thumbnail', ''),
                        "captions_available": bool(info.get('subtitles', {})),
                        "url": url
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