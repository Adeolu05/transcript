"""
Telegram per-user preferences (preferred file format, timestamps on/off).

Stored in Redis when REDIS_URL is set, so they survive restarts and deploys,
and expire after TELEGRAM_PREFS_TTL_DAYS of inactivity. Otherwise, or if Redis
errors, they live in process memory as before.
"""

from __future__ import annotations

from typing import Any, Dict

import redis

from app.core.config import settings
from app.core.languages import DEFAULT_LANGUAGE, LANGUAGE_CODES
from app.core.redis_client import get_redis, warn_fallback

FILE_FORMATS = ("txt", "pdf", "docx", "srt", "vtt")
DEFAULTS: Dict[str, Any] = {
    "last_file_format": "txt",
    "last_include_timestamps": False,
    "language": DEFAULT_LANGUAGE,
}

_memory: Dict[str, Dict[str, Any]] = {}


def _key(user_id: str) -> str:
    return f"tf:tgprefs:{user_id}"


def _decode(raw: Dict[str, str]) -> Dict[str, Any]:
    """Redis hash (all strings) → typed prefs, ignoring unknown/invalid values."""
    prefs = dict(DEFAULTS)
    if raw.get("last_file_format") in FILE_FORMATS:
        prefs["last_file_format"] = raw["last_file_format"]
    if raw.get("language") in LANGUAGE_CODES:
        prefs["language"] = raw["language"]
    if raw.get("last_include_timestamps") in ("0", "1"):
        prefs["last_include_timestamps"] = raw["last_include_timestamps"] == "1"
    return prefs


def get_prefs(user_id: str) -> Dict[str, Any]:
    client = get_redis()
    if client is not None:
        try:
            return _decode(client.hgetall(_key(user_id)))
        except redis.RedisError as e:
            warn_fallback("telegram prefs", e)
    return dict(_memory.get(user_id, DEFAULTS))


def set_prefs(user_id: str, **updates: Any) -> None:
    unknown = set(updates) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"Unknown preference(s): {sorted(unknown)}")

    _memory[user_id] = {**_memory.get(user_id, DEFAULTS), **updates}

    client = get_redis()
    if client is None:
        return
    encoded = {
        k: ("1" if v else "0") if isinstance(v, bool) else str(v) for k, v in updates.items()
    }
    try:
        pipe = client.pipeline(transaction=True)
        pipe.hset(_key(user_id), mapping=encoded)
        pipe.expire(_key(user_id), max(1, settings.telegram_prefs_ttl_days) * 86400)
        pipe.execute()
    except redis.RedisError as e:
        warn_fallback("telegram prefs", e)
