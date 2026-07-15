"""A tiny in-memory token-bucket rate limiter.

Used to bound how often a *public* endpoint may trigger outbound calls to the free
OSM services (Overpass/Nominatim). `/api/scrape` already had its own ad-hoc throttle;
`/api/nearby-stores` did not, so a stranger iterating coordinates could make this server
hammer Overpass and get *our* IP rate-limited. The limiter caps that fan-out.

Process-local (matches the single free-tier worker) and thread-safe. The clock is
injectable so tests can advance time deterministically without sleeping.
"""
from __future__ import annotations

import threading
import time
from typing import Callable


class RateLimiter:
    """Classic token bucket: starts full, refills at `refill_per_s` up to `capacity`,
    and `allow()` spends one token (returning False when the bucket is empty)."""

    def __init__(
        self,
        capacity: float,
        refill_per_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._capacity = float(capacity)
        self._refill = float(refill_per_s)
        self._clock = clock
        self._tokens = float(capacity)
        self._last = clock()
        self._lock = threading.Lock()

    def allow(self, cost: float = 1.0) -> bool:
        """Spend `cost` tokens if available; refill lazily based on elapsed time."""
        with self._lock:
            now = self._clock()
            elapsed = max(0.0, now - self._last)
            self._last = now
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill)
            if self._tokens >= cost:
                self._tokens -= cost
                return True
            return False
