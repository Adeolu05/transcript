"""
Anonymous product analytics — structured JSON event logging.

No PII, no raw URLs. Events are written as single JSON lines to stdout
via the application logger, ready for any log aggregator.
"""

import json
import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import settings
from app.utils.logging_config import logger

# Plain SHA-256 of an IPv4 address or Telegram ID is reversible by enumeration,
# so identifiers are keyed. Without LOG_HASH_SECRET the key lives per process.
_HASH_KEY = (settings.log_hash_secret or secrets.token_hex(32)).encode()

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
    "language_changed",
    "summary_clicked",
    "summary_succeeded",
    "summary_failed",
    # Telegram
    "tg_link_received",
    "tg_extract_succeeded",
    "tg_extract_failed",
    "tg_preview_clicked",
    "tg_download_clicked",
    "tg_rate_limited",
    # Telegram command usage
    "tg_cmd_start",
    "tg_cmd_help",
    "tg_cmd_extract",
    "tg_cmd_formats",
    "tg_cmd_privacy",
    "tg_cmd_status",
    "tg_sample_clicked",
    "tg_cmd_language",
    "tg_language_set",
    "tg_summary_clicked",
}

# Props keys we accept (everything else is stripped)
ALLOWED_PROPS = {
    "provider",
    "file_format",
    "include_timestamps",
    "duration_seconds_bucket",
    "error_code",
    "language",
    "translated",
    "cached",
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
    """Keyed one-way hash of an identifier (IP, Telegram user ID) for logs."""
    return hmac.new(_HASH_KEY, raw.encode(), hashlib.sha256).hexdigest()[:16]


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
