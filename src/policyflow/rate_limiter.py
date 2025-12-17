"""Rate limiter for LLM requests."""

import time
from threading import Lock
from typing import Optional


class RateLimiter:
    """Manages rate limiting using token bucket algorithm."""

    def __init__(self, rate_limit: Optional[int]):
        """
        Initialize rate limiter.

        Args:
            rate_limit: Requests per minute, None = unlimited
        """
        self._rate_limit = rate_limit
        self._lock = Lock()

        # Initialize token bucket state
        if self._rate_limit is not None:
            self._tokens = float(self._rate_limit)
            self._last_update = time.time()

    def wait_if_needed(self) -> None:
        """
        Check and update rate limit using token bucket algorithm.
        Waits if rate limit is exceeded.
        """
        if self._rate_limit is None:
            return

        with self._lock:
            now = time.time()
            time_passed = now - self._last_update

            # Refill tokens based on time passed (tokens per second = rate_limit / 60)
            refill_rate = self._rate_limit / 60.0
            self._tokens = min(
                self._rate_limit, self._tokens + (time_passed * refill_rate)
            )

            # If we have tokens, consume one
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                self._last_update = now
                return

            # Need to wait for tokens
            wait_time = (1.0 - self._tokens) / refill_rate

        # Wait outside the lock
        time.sleep(wait_time)

        # Update tokens after waiting
        with self._lock:
            self._tokens = 0.0
            self._last_update = time.time()
