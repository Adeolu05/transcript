"""
Anonymous product analytics — structured JSON event logging.

No PII, no raw URLs. Events are written as single JSON lines to stdout
via the application logger, ready for any log aggregator.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.utils.logging_config import logger

# ---------------------------------------------------------------------------
# Event allowlist
# ---------------------------------------------------------------------------
ALLOWED_EVENTS = {
    # Web
    "app_opened",
    "extract_clicked",
    "extract_succeeded",
    "extract_failed",
    "preview_shown",
    "download_clicked",
    "download_succeeded",
    "download_failed",
    "new_transcript_clicked",
    # Telegram
    "tg_link_received",
    "tg_extract_succeeded",
    "tg_extract_failed",
    "tg_preview_clicked",
    "tg_download_clicked",
    "tg_rate_limited",
}

# Props keys we accept (everything else is stripped)
ALLOWED_PROPS = {
    "provider",
    "file_format",
    "include_timestamps",
    "duration_seconds_bucket",
    "error_code",
}

# Maximum payload size (bytes) — reject anything larger
MAX_PAYLOAD_BYTES = 4096


# ---------------------------------------------------------------------------
# Duration bucketing (no precise duration leaks)
# ---------------------------------------------------------------------------
def bucket_duration(seconds: Optional[int]) -> Optional[str]:
    """Bucket a duration in seconds into a privacy-safe range string."""
    if seconds is None:
        return None
    if seconds <= 600:
        return "0-600"
    if seconds <= 1800:
        return "600-1800"
    if seconds <= 3600:
        return "1800-3600"
    return "3600+"


def hash_identifier(raw: str) -> str:
    """One-way SHA-256 hash of an identifier (e.g. Telegram user ID)."""
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Core logging
# ---------------------------------------------------------------------------
class TelemetryService:
    """Writes anonymous product events as structured JSON log lines."""

    @staticmethod
    def log_event(
        *,
        event_name: str,
        session_id: str,
        app_source: str,
        props: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Validate and log one event. Returns True if accepted."""
        if event_name not in ALLOWED_EVENTS:
            return False

        if app_source not in ("web", "telegram"):
            return False

        # Sanitise props — keep only allowed keys
        clean_props: Dict[str, Any] = {}
        if props:
            for key in ALLOWED_PROPS:
                if key in props:
                    clean_props[key] = props[key]

        record = {
            "event": event_name,
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id[:64],   # cap length
            "app_source": app_source,
            "props": clean_props,
        }

        logger.info(f"TELEMETRY {json.dumps(record, separators=(',', ':'))}")
        return True
