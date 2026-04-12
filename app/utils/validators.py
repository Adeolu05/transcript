import re
from urllib.parse import urlparse, parse_qs

# YouTube video IDs are 11 characters from this alphabet (standard watch/shorts IDs).
_YOUTUBE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")

_YOUTUBE_NETLOCS = frozenset(
    {
        "www.youtube.com",
        "youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "www.youtube-nocookie.com",
        "youtube-nocookie.com",
        "youtu.be",
    }
)

_VIMEO_NETLOCS = frozenset({"vimeo.com", "www.vimeo.com", "player.vimeo.com"})

# Vimeo numeric video IDs (allow short legacy IDs through long current IDs).
_VIMEO_ID_RE = re.compile(r"^\d{1,20}$")


def _normalize_youtube_id(raw: str) -> str:
    if not raw:
        raise ValueError("Invalid YouTube URL")
    video_id = raw.strip().split("/")[0]
    if not _YOUTUBE_ID_RE.fullmatch(video_id):
        raise ValueError("Invalid YouTube URL")
    return video_id


def validate_youtube_url(url: str) -> str:
    """
    Validates a YouTube URL and returns the video ID.
    Raises ValueError if the URL is invalid.
    """
    if not url:
        raise ValueError("URL cannot be empty")

    parsed_url = urlparse(url)
    netloc = (parsed_url.netloc or "").lower()

    if netloc not in _YOUTUBE_NETLOCS:
        raise ValueError("Invalid YouTube URL")

    if netloc == "youtu.be":
        path = parsed_url.path.lstrip("/")
        return _normalize_youtube_id(path)

    query = parse_qs(parsed_url.query)
    if "v" in query and query["v"][0]:
        return _normalize_youtube_id(query["v"][0])

    path_segs = [s for s in parsed_url.path.split("/") if s]
    if len(path_segs) >= 2 and path_segs[0] == "shorts":
        return _normalize_youtube_id(path_segs[1])
    if len(path_segs) >= 2 and path_segs[0] == "embed":
        return _normalize_youtube_id(path_segs[1])

    raise ValueError("Invalid YouTube URL")


def validate_vimeo_url(url: str) -> str:
    """
    Validates a Vimeo URL and returns the video ID.
    Raises ValueError if the URL is invalid.
    """
    if not url:
        raise ValueError("URL cannot be empty")

    parsed_url = urlparse(url)
    netloc = (parsed_url.netloc or "").lower()

    if netloc in ("vimeo.com", "www.vimeo.com"):
        path_parts = parsed_url.path.strip("/").split("/")
        if path_parts and _VIMEO_ID_RE.fullmatch(path_parts[0]):
            return path_parts[0]

    elif netloc == "player.vimeo.com":
        if parsed_url.path.startswith("/video/"):
            video_id = parsed_url.path.split("/")[2]
            if _VIMEO_ID_RE.fullmatch(video_id):
                return video_id

    raise ValueError("Invalid Vimeo URL")


def detect_platform(url: str) -> str:
    """
    Detects the video platform from URL.
    Returns 'youtube' or 'vimeo'.
    Raises ValueError if platform is not supported.
    """
    parsed_url = urlparse(url)
    netloc = (parsed_url.netloc or "").lower()

    if netloc in _YOUTUBE_NETLOCS:
        return "youtube"
    if netloc in _VIMEO_NETLOCS:
        return "vimeo"

    raise ValueError("Unsupported video platform")
