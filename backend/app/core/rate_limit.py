"""Small in-process sliding-window rate limiter.

Suitable for a single-process deployment (the documented local/demo setup).
For multi-worker production deployments this should be replaced by a Redis
backed limiter; this limitation is documented in the README.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

_AUTH_PATHS = ("/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED or request.method == "OPTIONS":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        is_auth = request.url.path in _AUTH_PATHS
        limit = settings.AUTH_RATE_LIMIT_REQUESTS if is_auth else settings.RATE_LIMIT_REQUESTS
        bucket = f"{client_ip}:{'auth' if is_auth else 'api'}"
        now = time.monotonic()
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        hits = self._hits[bucket]
        while hits and now - hits[0] > window:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = max(1, int(window - (now - hits[0])))
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests. Please retry later.",
                    }
                },
            )
        hits.append(now)
        return await call_next(request)
