import requests
import re
import json
import webvtt
from io import StringIO
from typing import List, Dict, Optional

def get_vimeo_transcript(video_id: str, url: str = '') -> Dict:
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
        
        response = requests.get(player_url, headers=headers, timeout=10)
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
            raise Exception("No text tracks found for this video")
        
        text_tracks_json = match.group(1)
        text_tracks = json.loads(text_tracks_json)
        
        if not text_tracks or len(text_tracks) == 0:
            raise Exception("No transcripts available for this video")
        
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
             raise Exception("No usable text tracks available")
            
        language = selected_track.get('lang', 'en')
        vtt_url = selected_track.get('url')
        
        if not vtt_url:
            raise Exception("No transcript URL found")
        
        # Download the VTT file
        vtt_response = requests.get(vtt_url, timeout=10)
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
        
    except requests.RequestException as e:
        if "403" in str(e):
            raise Exception("This video is private or restricted. Only public Vimeo videos with captions are supported.")
        elif "404" in str(e):
            raise Exception("Video not found. Please check the URL.")
        raise Exception(f"Failed to fetch Vimeo video: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse Vimeo text tracks: {str(e)}")
    except Exception as e:
        raise Exception(f"Error extracting Vimeo transcript: {str(e)}")

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
        raise Exception(f"Failed to parse VTT content: {str(e)}")
    
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
