import re
from urllib.parse import urlparse, parse_qs

def validate_youtube_url(url: str) -> str:
    """
    Validates a YouTube URL and returns the video ID.
    Raises ValueError if the URL is invalid.
    """
    if not url:
        raise ValueError("URL cannot be empty")

    parsed_url = urlparse(url)
    
    if parsed_url.netloc in ["www.youtube.com", "youtube.com"]:
        query = parse_qs(parsed_url.query)
        if "v" in query:
            return query["v"][0]
    elif parsed_url.netloc == "youtu.be":
        return parsed_url.path.lstrip("/")
    
    # Handle shorts
    if parsed_url.path.startswith("/shorts/"):
        return parsed_url.path.split("/")[2]

    raise ValueError("Invalid YouTube URL")

def validate_vimeo_url(url: str) -> str:
    """
    Validates a Vimeo URL and returns the video ID.
    Raises ValueError if the URL is invalid.
    """
    if not url:
        raise ValueError("URL cannot be empty")
    
    parsed_url = urlparse(url)
    
    # Handle vimeo.com/123456789
    if parsed_url.netloc in ["vimeo.com", "www.vimeo.com"]:
        # Extract video ID from path
        path_parts = parsed_url.path.strip("/").split("/")
        if path_parts and path_parts[0].isdigit():
            return path_parts[0]
    
    # Handle player.vimeo.com/video/123456789
    elif parsed_url.netloc == "player.vimeo.com":
        if parsed_url.path.startswith("/video/"):
            video_id = parsed_url.path.split("/")[2]
            if video_id.isdigit():
                return video_id
    
    raise ValueError("Invalid Vimeo URL")

def detect_platform(url: str) -> str:
    """
    Detects the video platform from URL.
    Returns 'youtube' or 'vimeo'.
    Raises ValueError if platform is not supported.
    """
    parsed_url = urlparse(url)
    
    if parsed_url.netloc in ["www.youtube.com", "youtube.com", "youtu.be"]:
        return "youtube"
    elif parsed_url.netloc in ["vimeo.com", "www.vimeo.com", "player.vimeo.com"]:
        return "vimeo"
    
    raise ValueError("Unsupported video platform")
