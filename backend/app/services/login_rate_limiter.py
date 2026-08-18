from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class LoginRateLimiter:
    """Process-local sliding-window limiter for account and client failures."""

    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, key: str, *, now: float, window_seconds: int) -> None:
        failures = self._failures[key]
        cutoff = now - window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        if not failures:
            self._failures.pop(key, None)

    def is_blocked(
        self, keys: tuple[str, ...], *, limit: int, window_seconds: int
    ) -> bool:
        if limit <= 0 or window_seconds <= 0:
            return False
        now = monotonic()
        with self._lock:
            for key in keys:
                self._prune(key, now=now, window_seconds=window_seconds)
            return any(
                len(self._failures.get(key, ())) >= limit for key in keys
            )

    def record_failure(self, keys: tuple[str, ...]) -> None:
        now = monotonic()
        with self._lock:
            for key in keys:
                self._failures[key].append(now)

    def clear(self, keys: tuple[str, ...]) -> None:
        with self._lock:
            for key in keys:
                self._failures.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_rate_limiter = LoginRateLimiter()
