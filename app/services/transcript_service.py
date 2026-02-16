from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, VideoUnavailable
from typing import List, Dict, Optional
from app.utils.validators import detect_platform, validate_youtube_url, validate_vimeo_url
from app.services.vimeo_service import get_vimeo_transcript

def get_transcript_from_url(url: str) -> List[Dict]:
    """
    Unified function to get transcript from any supported platform.
    Detects platform and routes to appropriate service.
    """
    try:
        platform = detect_platform(url)
        
        if platform == "youtube":
            video_id = validate_youtube_url(url)
            return get_youtube_transcript(video_id)
        elif platform == "vimeo":
            video_id = validate_vimeo_url(url)
            return get_vimeo_transcript(video_id)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    except ValueError as e:
        raise Exception(str(e))
    except Exception as e:
        raise e

def get_youtube_transcript(video_id: str, languages: List[str] = ['en']) -> List[Dict]:
    """
    Fetches the transcript for a given YouTube video ID.
    """
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=languages)
        # Convert FetchedTranscriptSnippet objects to dictionaries
        return [{'text': item.text, 'start': item.start, 'duration': item.duration} 
                for item in transcript]
    except TranscriptsDisabled:
        raise Exception("Transcripts are disabled for this video.")
    except VideoUnavailable:
        raise Exception("Video is unavailable.")
    except Exception as e:
        if "No transcript found" in str(e):
             raise Exception("No transcript found for the requested languages.")
        raise e

# Legacy function for backward compatibility
def get_transcript(video_id: str, languages: List[str] = ['en']) -> Optional[List[Dict]]:
    """
    Legacy function. Use get_youtube_transcript instead.
    Fetches the transcript for a given YouTube video ID.
    Tries to fetch validation for the specified languages, defaulting to English.
    """
    return get_youtube_transcript(video_id, languages)
