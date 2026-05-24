"""Sliding-window per-IP rate limiting middleware."""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_SKIP_PATHS = frozenset({"/health", "/metrics", "/healthz", "/readyz"})


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-process sliding-window rate limiter."""

    def __init__(self, app, calls_per_minute: int = 100, window_seconds: float = 60.0):
        super().__init__(app)
        self._limit = calls_per_minute
        self._window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.monotonic()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        ip = (request.client.host if request.client else None) or "unknown"
        now = time.monotonic()

        if now - self._last_cleanup > 300:
            self._buckets = {k: v for k, v in self._buckets.items() if v}
            self._last_cleanup = now

        window_start = now - self._window
        bucket = [t for t in self._buckets[ip] if t > window_start]

        if len(bucket) >= self._limit:
            oldest = bucket[0]
            retry_after = int(self._window - (now - oldest)) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please slow down."},
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
        self._buckets[ip] = bucket
        return await call_next(request)
