import requests
import re
import json
import time
import webvtt
from io import StringIO
from typing import List, Dict, Optional

from app.core.errors import ErrorCode, TranscriptFetchError

_NO_CAPTIONS = "No captions are available for this Vimeo video."
_REQUEST_TIMEOUT = 10


def _timeout(deadline: Optional[float]) -> float:
    """Per-request timeout, never past the caller's deadline (time.monotonic())."""
    if deadline is None:
        return _REQUEST_TIMEOUT
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TranscriptFetchError(
            ErrorCode.UPSTREAM_TIMEOUT, "Transcript provider did not respond in time."
        )
    return min(_REQUEST_TIMEOUT, remaining)


def get_vimeo_transcript(video_id: str, url: str = '', deadline: Optional[float] = None) -> Dict:
    """
    Fetches the transcript for a given Vimeo video ID.
    Extracts text tracks from Vimeo player config and parses VTT format.
    Returns standard PRD struct.
    """
    try:
        # Fetch the Vimeo PLAYER page (not the main video page)
        player_url = f"https://player.vimeo.com/video/{video_id}"
        
        # Add headers to mimic a browser and avoid 403 errors
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': f'https://vimeo.com/{video_id}',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.get(player_url, headers=headers, timeout=_timeout(deadline))
        response.raise_for_status()
        
        html_content = response.text
        
        # Extract title
        title_match = re.search(r'<title>([^<]+)</title>', html_content)
        title = title_match.group(1).replace(" on Vimeo", "") if title_match else f"Vimeo Video {video_id}"
        
        # Extract duration
        duration_match = re.search(r'"duration"\s*:\s*(\d+)', html_content)
        duration = int(duration_match.group(1)) if duration_match else 0
        
        # Extract the embedded JSON config from the player HTML
        # Look for pattern: "text_tracks":[...]
        config_pattern = r'"text_tracks"\s*:\s*(\[.*?\])'
        match = re.search(config_pattern, html_content, re.DOTALL)
        
        if not match:
            raise TranscriptFetchError(ErrorCode.TRANSCRIPT_NOT_AVAILABLE, _NO_CAPTIONS)
        
        text_tracks_json = match.group(1)
        text_tracks = json.loads(text_tracks_json)
        
        if not text_tracks or len(text_tracks) == 0:
            raise TranscriptFetchError(ErrorCode.TRANSCRIPT_NOT_AVAILABLE, _NO_CAPTIONS)
        
        # Use the first available text track (preferably English)
        selected_track = None
        for track in text_tracks:
            if track.get('lang') == 'en':
                selected_track = track
                break
        
        # If no English, use the first one
        if not selected_track and len(text_tracks) > 0:
            selected_track = text_tracks[0]
            
        if not selected_track:
            raise TranscriptFetchError(ErrorCode.TRANSCRIPT_NOT_AVAILABLE, _NO_CAPTIONS)
            
        language = selected_track.get('lang', 'en')
        vtt_url = selected_track.get('url')
        
        if not vtt_url:
            raise TranscriptFetchError(ErrorCode.TRANSCRIPT_NOT_AVAILABLE, _NO_CAPTIONS)
        
        # Download the VTT file
        vtt_response = requests.get(vtt_url, timeout=_timeout(deadline))
        vtt_response.raise_for_status()
        
        # Parse VTT content
        vtt_content = vtt_response.text
        segments = parse_vtt(vtt_content)
        
        return {
            "provider": "vimeo",
            "source_url": url,
            "video_id": video_id,
            "title": title,
            "language": language,
            "duration_seconds": duration,
            "segments": segments
        }
        
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 403:
            raise TranscriptFetchError(
                ErrorCode.TRANSCRIPT_NOT_AVAILABLE,
                "This video is private or restricted. Only public Vimeo videos with captions are supported.",
            ) from e
        if status == 404:
            raise TranscriptFetchError(
                ErrorCode.TRANSCRIPT_NOT_AVAILABLE, "Video not found. Please check the URL."
            ) from e
        raise TranscriptFetchError(
            ErrorCode.TRANSCRIPT_NOT_AVAILABLE, "Vimeo did not return this video. Try again later."
        ) from e
    except requests.Timeout as e:
        raise TranscriptFetchError(
            ErrorCode.UPSTREAM_TIMEOUT, "Transcript provider did not respond in time."
        ) from e
    except requests.RequestException as e:
        raise TranscriptFetchError(
            ErrorCode.TRANSCRIPT_NOT_AVAILABLE, "Could not reach Vimeo. Try again later."
        ) from e
    except json.JSONDecodeError as e:
        raise TranscriptFetchError(ErrorCode.TRANSCRIPT_NOT_AVAILABLE, _NO_CAPTIONS) from e

def parse_vtt(vtt_content: str) -> List[Dict]:
    """
    Parses VTT (WebVTT) content and returns a list of transcript dictionaries.
    """
    transcript = []
    
    try:
        # Use webvtt library to parse
        vtt_io = StringIO(vtt_content)
        
        for caption in webvtt.read_buffer(vtt_io):
            # Convert timestamp to seconds
            start_seconds = timestamp_to_seconds(caption.start)
            end_seconds = timestamp_to_seconds(caption.end)
            duration = end_seconds - start_seconds
            
            transcript.append({
                'text': caption.text.strip(),
                'start': start_seconds,
                'duration': duration
            })
    
    except Exception as e:
        raise TranscriptFetchError(
            ErrorCode.TRANSCRIPT_NOT_AVAILABLE, "Vimeo captions could not be read."
        ) from e
    
    return transcript

def timestamp_to_seconds(timestamp: str) -> float:
    """
    Converts VTT timestamp (HH:MM:SS.mmm or MM:SS.mmm) to seconds.
    """
    parts = timestamp.split(':')
    
    if len(parts) == 3:
        # HH:MM:SS.mmm
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        # MM:SS.mmm
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    else:
        return float(timestamp)
