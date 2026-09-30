"""
backend/middleware/rate_limit.py
=================================
PURPOSE
    A minimal fixed-window rate limiter, per client IP. Good enough to stop a
    runaway script or a naive scraper on a student project; a production
    deployment would move this to the API gateway / a shared Redis counter so
    it works across multiple backend instances.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.limit = requests_per_minute
        self.window_seconds = 60
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        hits = self._hits[client_ip]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limited",
                         "message": "Too many requests. Please slow down and try again shortly."},
                headers={"Retry-After": str(self.window_seconds)},
            )
        hits.append(now)
        return await call_next(request)
