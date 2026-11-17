"""A per-key token-bucket rate limiter (in memory, one per process)."""

from __future__ import annotations

from collections.abc import Callable
import threading
import time


class RateLimiter:
    """Allow ``per_minute`` requests a minute per key, with a burst of ``burst``.

    ``per_minute=0`` disables limiting.
    """

    def __init__(
        self,
        per_minute: int,
        burst: int | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.rate = per_minute / 60.0
        self.capacity = float(burst if burst is not None else max(1, per_minute // 6))
        self._clock = clock
        self._state: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> float:
        """Return 0 if the request is allowed, else seconds until it would be."""

        if self.rate <= 0:
            return 0.0
        now = self._clock()
        with self._lock:
            tokens, last = self._state.get(key, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.rate)
            if tokens >= 1.0:
                self._state[key] = (tokens - 1.0, now)
                return 0.0
            self._state[key] = (tokens, now)
            return (1.0 - tokens) / self.rate
