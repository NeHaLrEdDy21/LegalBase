"""
Token-bucket rate limiter middleware for FastAPI.

Each unique client IP gets its own bucket.  Requests exceeding the
configured rate return HTTP 429 with a ``Retry-After`` header.

Configuration is read from :class:`~app.config.settings.Settings`.
"""
import logging
import time
from collections import defaultdict
from threading import Lock

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class _Bucket:
    """Leaky/token-bucket state for a single client."""

    __slots__ = ("tokens", "last_refill")

    def __init__(self, capacity: float) -> None:
        self.tokens: float = capacity
        self.last_refill: float = time.monotonic()


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window token-bucket rate limiter.

    Parameters
    ----------
    app :
        The ASGI application to wrap.
    requests_per_window : int
        Maximum requests allowed per ``window_seconds``.
    window_seconds : int
        Duration of the rate-limiting window.
    """

    def __init__(
        self,
        app,
        requests_per_window: int = 60,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.capacity = float(requests_per_window)
        self.refill_rate = float(requests_per_window) / float(window_seconds)
        self.window_seconds = window_seconds
        self._buckets: dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(self.capacity)
        )
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = self._get_client_ip(request)

        allowed, retry_after = self._consume(client_ip)

        if not allowed:
            logger.warning("Rate limit exceeded for IP '%s'.", client_ip)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please slow down.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        return response

    # ── private helpers ────────────────────────────────────────────────────────

    def _consume(self, client_ip: str) -> tuple[bool, int]:
        """
        Consume one token from the bucket.

        Returns
        -------
        (allowed, retry_after)
            *allowed* is True when the request is permitted.
            *retry_after* is the number of seconds until the next token.
        """
        with self._lock:
            bucket = self._buckets[client_ip]
            now = time.monotonic()
            elapsed = now - bucket.last_refill
            bucket.tokens = min(
                self.capacity, bucket.tokens + elapsed * self.refill_rate
            )
            bucket.last_refill = now

            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True, 0

            wait = (1.0 - bucket.tokens) / self.refill_rate
            return False, max(1, int(wait))

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
