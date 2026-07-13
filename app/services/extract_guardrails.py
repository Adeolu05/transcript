"""
Shared extract-time guardrails used by the HTTP API and Telegram bot.

Keeps duration / size policy in one place so interfaces stay consistent.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.errors import AppError, ErrorCode


def estimate_duration_seconds(transcript_data: Dict[str, Any]) -> int:
    """
    Prefer provider duration; if missing/zero, estimate from last caption cue.
    Returns 0 only when no useful signal exists.
    """
    reported = int(transcript_data.get("duration_seconds") or 0)
    if reported > 0:
        return reported

    segments: List[Dict[str, Any]] = transcript_data.get("segments") or []
    if not segments:
        return 0

    last = segments[-1]
    try:
        start = float(last.get("start") or 0)
        dur = float(last.get("duration") or 0)
        est = int(start + dur)
        return est if est > 0 else 0
    except (TypeError, ValueError):
        return 0


def segment_count(transcript_data: Dict[str, Any]) -> int:
    segments = transcript_data.get("segments") or []
    return len(segments) if isinstance(segments, list) else 0


def raw_caption_char_count(transcript_data: Dict[str, Any]) -> int:
    segments = transcript_data.get("segments") or []
    total = 0
    for entry in segments:
        if not isinstance(entry, dict):
            continue
        text = entry.get("text") or ""
        if isinstance(text, str):
            total += len(text)
    return total


def enforce_transcript_guardrails(
    transcript_data: Dict[str, Any],
    *,
    formatted_text: Optional[str] = None,
) -> int:
    """
    Raises AppError when limits are exceeded.
    Returns the effective duration (reported or estimated) for logging/response.
    """
    n_seg = segment_count(transcript_data)
    if n_seg > settings.max_transcript_segments:
        raise AppError(
            ErrorCode.VIDEO_TOO_LONG,
            "Transcript is too large to process (too many caption segments).",
            400,
        )

    caption_chars = raw_caption_char_count(transcript_data)
    if caption_chars > settings.max_raw_text_length:
        raise AppError(
            ErrorCode.VIDEO_TOO_LONG,
            "Transcript is too large to process.",
            400,
        )

    duration = estimate_duration_seconds(transcript_data)
    # Persist effective duration so callers log consistent values
    if not (transcript_data.get("duration_seconds") or 0) and duration > 0:
        transcript_data["duration_seconds"] = duration

    if duration > settings.max_video_duration_seconds:
        raise AppError(
            ErrorCode.VIDEO_TOO_LONG,
            "Video exceeds maximum supported duration.",
            400,
        )

    # Unknown duration: if segment estimate is also 0 but we have many segments,
    # still bounded by max_transcript_segments / max_raw_text_length above.
    # Optionally reject completely empty duration with huge segment density:
    if duration <= 0 and n_seg > max(100, settings.max_transcript_segments // 2):
        raise AppError(
            ErrorCode.VIDEO_TOO_LONG,
            "Video duration could not be verified and caption volume is too high.",
            400,
        )

    if formatted_text is not None and len(formatted_text) > settings.max_raw_text_length:
        raise AppError(
            ErrorCode.VIDEO_TOO_LONG,
            "Transcript is too large to process.",
            400,
        )

    return duration
