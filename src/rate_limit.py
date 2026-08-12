"""Sliding-window in-memory rate limiter per client key."""

from __future__ import annotations

import time


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = {}
        self._last_cleanup: float = time.time()

    def is_allowed(
        self, key: str, max_requests: int, window_seconds: float = 60.0
    ) -> bool:
        if max_requests <= 0:
            return True
        now = time.time()
        if now - self._last_cleanup > 300:
            self._cleanup(now, window_seconds)

        timestamps = self._requests.setdefault(key, [])
        cutoff = now - window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        if len(timestamps) >= max_requests:
            return False

        timestamps.append(now)
        return True

    def _cleanup(self, now: float, window_seconds: float) -> None:
        self._last_cleanup = now
        cutoff = now - window_seconds
        stale_keys = [
            k for k, ts in self._requests.items() if not ts or ts[-1] < cutoff
        ]
        for k in stale_keys:
            del self._requests[k]

    def reset(self) -> None:
        self._requests.clear()
        self._last_cleanup = time.time()
