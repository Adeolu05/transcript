import json
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from app.utils.logging_config import logger
from app.utils.validators import validate_vimeo_url, validate_youtube_url


class MetadataService:
    """
    Product intelligence layer. Tracks metadata, success rates, and errors.
    Does NOT store transcript text. Emits JSON-serialisable dicts for analytics.
    """

    @staticmethod
    def calculate_metrics(text: str) -> Dict[str, int]:
        """Calculates standard reading metrics from raw text."""
        words = len(text.split())
        reading_time_seconds = int((words / 238) * 60) if words > 0 else 0
        return {
            "word_count": words,
            "reading_time_seconds": reading_time_seconds,
        }

    @staticmethod
    def log_success(
        video_id: str,
        provider: str,
        duration_seconds: int,
        processing_time_ms: int,
        word_count: int,
        format_requested: str,
        file_type: str,
    ):
        """Logs a successful extraction workflow as structured JSON."""
        log_data = {
            "event": "transcript_success",
            "video_id": video_id,
            "provider": provider,
            "duration_seconds": duration_seconds,
            "processing_time_ms": processing_time_ms,
            "word_count": word_count,
            "format_requested": format_requested,
            "file_type": file_type,
        }
        logger.info(json.dumps(log_data))

    @staticmethod
    def _video_ref(url: str, platform: str) -> Dict[str, Optional[str]]:
        """
        Public video ID (as success logs already record) plus host — never the
        raw URL, whose query/path can carry share tokens or tracking params.
        """
        validate = {"youtube": validate_youtube_url, "vimeo": validate_vimeo_url}.get(platform)
        video_id = None
        if validate and url:
            try:
                video_id = validate(url)
            except ValueError:
                pass
        host = (urlparse(url).hostname or "")[:100] if url else ""
        return {"video_id": video_id, "host": host}

    @staticmethod
    def log_failure(
        url: str,
        platform: str,
        error_code: str,
        error_message: str,
        processing_time_ms: int,
        format_requested: str = "unknown",
    ):
        """Logs a failed extraction workflow as structured JSON."""
        log_data = {
            "event": "transcript_failure",
            **MetadataService._video_ref(url, platform),
            "provider": platform,
            "error_code": error_code,
            "error_message": error_message,
            "processing_time_ms": processing_time_ms,
            "format_requested": format_requested,
        }
        logger.error(json.dumps(log_data))

    @staticmethod
    def log_rate_limit_block(identifier: str):
        """Logs a rate limit block event as structured JSON."""
        log_data = {
            "event": "rate_limit_block",
            "identifier": identifier,
        }
        logger.warning(json.dumps(log_data))

    @staticmethod
    def log_video_too_long(
        video_id: str,
        provider: str,
        duration_seconds: int,
        processing_time_ms: int,
    ):
        """Logs a video-too-long rejection as structured JSON."""
        log_data = {
            "event": "video_too_long",
            "video_id": video_id,
            "provider": provider,
            "duration_seconds": duration_seconds,
            "processing_time_ms": processing_time_ms,
            "error_code": "VIDEO_TOO_LONG",
        }
        logger.warning(json.dumps(log_data))
