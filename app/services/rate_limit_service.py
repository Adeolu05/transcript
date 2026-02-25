import time
from typing import Dict, Tuple

class RateLimitService:
    def __init__(self, limit: int = 100, window_seconds: int = 86400):
        # Store requests as {identifier: (count, reset_time)}
        self.limit = limit
        self.window_seconds = window_seconds
        self._store: Dict[str, Tuple[int, float]] = {}

    def is_allowed(self, identifier: str) -> bool:
        """
        Checks if the identifier (IP or Telegram User ID) has exceeded the rate limit.
        Returns True if allowed, False if blocked.
        """
        now = time.time()
        
        # Clean up expired entries lazily (optional for V1, but good practice)
        self._cleanup(now)
        
        if identifier not in self._store:
            # First request
            self._store[identifier] = (1, now + self.window_seconds)
            return True
            
        count, reset_time = self._store[identifier]
        
        if now > reset_time:
            # Window expired, reset count
            self._store[identifier] = (1, now + self.window_seconds)
            return True
            
        if count < self.limit:
            # Within window and limit
            self._store[identifier] = (count + 1, reset_time)
            return True
            
        return False
        
    def _cleanup(self, now: float):
        """Removes expired entries to prevent memory leaks."""
        expired = [k for k, v in self._store.items() if now > v[1]]
        for k in expired:
            del self._store[k]

# Global instance for V1 in-memory state
# In production Phase 2, this would be replaced with Redis
from app.core.config import settings
rate_limiter = RateLimitService(
    limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

def check_rate_limit(identifier: str) -> bool:
    return rate_limiter.is_allowed(identifier)
