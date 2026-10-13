import time
from typing import Dict, Optional, Tuple

import redis

from app.core.config import settings
from app.core.redis_client import get_redis, warn_fallback


class RateLimitService:
    """
    Fixed-window counter keyed by (bucket, identifier).

    With REDIS_URL set, counts are shared by every Gunicorn worker and the
    Telegram bot. Otherwise (or if Redis errors) each process keeps its own
    in-memory store, so effective limits can be up to ~N× the configured value.
    """

    def __init__(self) -> None:
        # { "bucket:identifier": (count, reset_time) }
        self._store: Dict[str, Tuple[int, float]] = {}

    def _limit_for_bucket(self, bucket: str) -> int:
        if bucket == "extract":
            return max(0, int(settings.rate_limit_requests))
        if bucket == "convert":
            return max(0, int(settings.rate_limit_convert_requests))
        if bucket == "events":
            return max(0, int(settings.rate_limit_events_requests))
        if bucket == "download":
            return max(0, int(settings.rate_limit_download_requests))
        return max(0, int(settings.rate_limit_requests))

    def is_allowed(self, identifier: str, bucket: str = "extract") -> bool:
        """
        Returns True if allowed, False if blocked.
        limit 0 means unlimited (always allowed).
        """
        limit = self._limit_for_bucket(bucket)
        if limit <= 0:
            return True

        window_seconds = max(1, int(settings.rate_limit_window_seconds))
        shared = self._redis_is_allowed(identifier, bucket, limit, window_seconds)
        if shared is not None:
            return shared

        now = time.time()
        self._cleanup(now)

        key = f"{bucket}:{identifier}"
        if key not in self._store:
            self._store[key] = (1, now + window_seconds)
            return True

        count, reset_time = self._store[key]

        if now > reset_time:
            self._store[key] = (1, now + window_seconds)
            return True

        if count < limit:
            self._store[key] = (count + 1, reset_time)
            return True

        return False

    @staticmethod
    def _redis_is_allowed(
        identifier: str, bucket: str, limit: int, window_seconds: int
    ) -> Optional[bool]:
        """Shared count via Redis; None means use the in-memory fallback."""
        client = get_redis()
        if client is None:
            return None
        key = f"tf:rl:{bucket}:{identifier}"
        try:
            # SET NX starts the window with its TTL; INCR counts this request
            pipe = client.pipeline(transaction=True)
            pipe.set(key, 0, ex=window_seconds, nx=True)
            pipe.incr(key)
            _, count = pipe.execute()
        except redis.RedisError as e:
            warn_fallback("rate limit", e)
            return None
        return int(count) <= limit

    def _cleanup(self, now: float) -> None:
        expired = [k for k, v in self._store.items() if now > v[1]]
        for k in expired:
            del self._store[k]


rate_limiter = RateLimitService()


def check_rate_limit(identifier: str, bucket: str = "extract") -> bool:
    return rate_limiter.is_allowed(identifier, bucket=bucket)
