# Content Analyzer: YouTube & GitHub

This Streamlit application combines powerful analysis capabilities for both YouTube videos and GitHub repositories. It provides automated transcription, summarization, and content analysis using AI.

## Features

### YouTube Analysis
- **Video Transcription:** Automatically generates transcripts from YouTube videos
- **Smart Chapters:** Creates AI-generated chapters based on video content
- **Content Summary:** Provides concise summaries of video content
- **Tag Generation:** Automatically generates relevant tags
- **Export to Capacities:** Save analysis results to Capacities platform

### GitHub Analysis
- **README Analysis:** Extracts and analyzes repository README files
- **Repository Structure:** Maps out repository structure and content
- **Content Extraction:** Retrieves and analyzes text-based file contents
- **Intelligent Filtering:** Automatically skips binary files during analysis

## Setup

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Set up environment variables in `.env`:
```
OPENAI_API_KEY=your_openai_api_key
CAPACITIES_API_KEY=your_capacities_api_key
CAPACITIES_SPACE_ID=your_capacities_space_id
GITHUB_TOKEN=your_github_token
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Enter either a YouTube URL or GitHub repository URL
3. The app will automatically detect the type of content and process it accordingly
4. View the analysis results and export them to Capacities if desired

## Requirements

- Python 3.8+
- FFmpeg (for audio processing)
- OpenAI API key
- Capacities account and API credentials
- GitHub personal access token

## Dependencies

Main Python packages:
- `streamlit`: Web interface
- `openai`: AI processing
- `youtube-transcript-api`: YouTube transcript fetching
- `yt-dlp`: YouTube video/audio downloading
- `pydub`: Audio processing
- `requests`: HTTP requests
- `python-dotenv`: Environment variable management

## License

This project is licensed under the MIT License - see the LICENSE file for details.
