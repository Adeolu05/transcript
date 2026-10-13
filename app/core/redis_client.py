"""
Optional shared Redis connection (REDIS_URL).

Callers must treat Redis as best-effort: get_redis() returns None when it is
not configured, and any redis.RedisError should fall back to in-memory state so
an outage degrades limits to per-process instead of taking the API down.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import redis

from app.core.config import settings
from app.utils.logging_config import logger

# Keep request latency bounded if Redis is slow or gone
_SOCKET_TIMEOUT_SECONDS = 0.5
_WARN_INTERVAL_SECONDS = 60

_client: Optional[redis.Redis] = None
_client_url = ""
_lock = threading.Lock()
_last_warning = 0.0


def get_redis() -> Optional[redis.Redis]:
    global _client, _client_url
    url = (settings.redis_url or "").strip()
    if not url:
        return None
    with _lock:
        if _client is None or _client_url != url:
            _client = redis.Redis.from_url(
                url,
                socket_timeout=_SOCKET_TIMEOUT_SECONDS,
                socket_connect_timeout=_SOCKET_TIMEOUT_SECONDS,
                decode_responses=True,
            )
            _client_url = url
        return _client


def warn_fallback(context: str, error: Exception) -> None:
    """Log a Redis failure at most once a minute (a dead Redis would flood logs)."""
    global _last_warning
    now = time.monotonic()
    if now - _last_warning >= _WARN_INTERVAL_SECONDS:
        _last_warning = now
        logger.warning("Redis unavailable (%s), using in-memory fallback: %s", context, error)
