from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class _SlidingWindowLimiter:
    """Small process-local sliding-window limiter for a single small web instance.

    Stale identities are periodically evicted so a bot rotating source addresses
    cannot grow the process dictionary forever. If the web tier is horizontally
    scaled, replace this implementation with a shared edge/store-backed limiter.
    """

    def __init__(self, *, cleanup_every: int = 128, max_idle_seconds: int = 7200) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._checks = 0
        self._cleanup_every = cleanup_every
        self._max_idle_seconds = max_idle_seconds

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._checks = 0

    def _cleanup(self, *, now: float) -> None:
        idle_before = now - self._max_idle_seconds
        stale = [key for key, events in self._events.items() if not events or events[-1] < idle_before]
        for key in stale:
            self._events.pop(key, None)

    def check(self, key: str, *, limit: int, window_seconds: int) -> int:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            self._checks += 1
            if self._checks % self._cleanup_every == 0:
                self._cleanup(now=now)

            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return max(1, int(window_seconds - (now - events[0])))
            events.append(now)
        return 0


_limiter = _SlidingWindowLimiter()


def request_client_key(request: Request) -> str:
    # Render supplies X-Forwarded-For. Use the first original-client value and
    # fall back to the ASGI peer for local development/tests.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        candidate = forwarded.split(",", 1)[0].strip()
        if candidate:
            return candidate[:128]
    return (request.client.host if request.client else "unknown")[:128]


def enforce_rate_limit(
    request: Request,
    *,
    bucket: str,
    identity: str | None = None,
    limit: int,
    window_seconds: int,
) -> None:
    key = f"{bucket}:{identity or request_client_key(request)}"
    retry_after = _limiter.check(key, limit=limit, window_seconds=window_seconds)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )


def reset_rate_limits() -> None:
    _limiter.reset()
