from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, VideoUnavailable
from typing import List, Dict, Optional
from app.utils.validators import detect_platform, validate_youtube_url, validate_vimeo_url
from app.services.vimeo_service import get_vimeo_transcript

import requests
import re
import json
from typing import Dict, List, Optional

def get_transcript_from_url(url: str) -> Dict:
    """
    Unified function to get transcript from any supported platform.
    Detects platform and routes to appropriate service.
    Returns standard PRD structured dict.
    """
    try:
        platform = detect_platform(url)
        
        if platform == "youtube":
            video_id = validate_youtube_url(url)
            return get_youtube_transcript(video_id, url=url)
        elif platform == "vimeo":
            video_id = validate_vimeo_url(url)
            return get_vimeo_transcript(video_id, url=url)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    except ValueError as e:
        raise Exception(str(e))
    except Exception as e:
        raise e

def _get_youtube_metadata(video_id: str) -> Dict:
    """Fetches video metadata directly from YouTube page."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.text
        
        # Extract title
        title_match = re.search(r'<meta name="title" content="([^"]+)">', html)
        title = title_match.group(1) if title_match else f"YouTube Video {video_id}"
        
        # Extract duration from initialData payload
        duration_match = re.search(r'"approxDurationMs":"(\d+)"', html)
        duration = int(int(duration_match.group(1)) / 1000) if duration_match else 0
        
        return {"title": title, "duration": duration}
    except Exception:
        return {"title": f"YouTube Video {video_id}", "duration": 0}

def get_youtube_transcript(video_id: str, languages: List[str] = ['en'], url: str = '') -> Dict:
    """
    Fetches the transcript for a given YouTube video ID.
    Returns the PRD structured dict.
    """
    try:
        # 1. Fetch metadata
        metadata = _get_youtube_metadata(video_id)
        
        # 2. Fetch transcript
        api = YouTubeTranscriptApi()
        raw_transcript = api.fetch(video_id, languages=languages)
        
        # 3. Format segments
        segments = [{'text': item.text, 'start': item.start, 'duration': item.duration} 
                for item in raw_transcript]
                
        # 4. Return exact PRD spec
        return {
            "provider": "youtube",
            "source_url": url,
            "video_id": video_id,
            "title": metadata["title"],
            "language": languages[0] if languages else "en",
            "duration_seconds": metadata["duration"],
            "segments": segments
        }
    except TranscriptsDisabled:
        raise Exception("Transcripts are disabled for this video.")
    except VideoUnavailable:
        raise Exception("Video is unavailable.")
    except Exception as e:
        if "No transcript found" in str(e):
             raise Exception("No transcript found for the requested languages.")
        raise e

# Legacy function for backward compatibility
def get_transcript(video_id: str, languages: List[str] = ['en']) -> Optional[Dict]:
    """
    Legacy function. Use get_youtube_transcript instead.
    Fetches the transcript for a given YouTube video ID.
    Tries to fetch validation for the specified languages, defaulting to English.
    """
    return get_youtube_transcript(video_id, languages)
