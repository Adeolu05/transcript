import time
from typing import Dict, Tuple

from app.core.config import settings


class RateLimitService:
    """
    In-memory sliding window counter keyed by (bucket, identifier).

    Multi-worker note: each Gunicorn worker has its own store, so effective
    limits can be up to ~N× the configured value under uniform load.
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

    def _cleanup(self, now: float) -> None:
        expired = [k for k, v in self._store.items() if now > v[1]]
        for k in expired:
            del self._store[k]


rate_limiter = RateLimitService()


def check_rate_limit(identifier: str, bucket: str = "extract") -> bool:
    return rate_limiter.is_allowed(identifier, bucket=bucket)
