"""
In-memory and Redis-backed rate limiting middleware.
"""

from __future__ import annotations

import inspect
import time
from collections import defaultdict
from typing import Any

from raft.config.settings import settings
from raft.core.exceptions import HTTPException
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.base import CallNext


class _MemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds

        # Clean up stale/empty IP keys to prevent memory leaks
        if len(self._hits) > 50:
            dead_keys = [
                k for k, stamps in self._hits.items()
                if not stamps or stamps[-1] <= window_start
            ]
            for k in dead_keys:
                del self._hits[k]

        hits = [stamp for stamp in self._hits[key] if stamp > window_start]
        if len(hits) >= self.max_requests:
            if hits:
                self._hits[key] = hits
            else:
                self._hits.pop(key, None)
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


class _RedisRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def allow(self, key: str) -> bool:
        from raft.redis.client import get_redis, redis_key

        redis = get_redis()
        bucket = redis_key("ratelimit:", key)
        count = await redis.incr(bucket)
        if count == 1:
            await redis.expire(bucket, self.window_seconds)
        return int(count) <= self.max_requests


_limiter: _MemoryRateLimiter | _RedisRateLimiter | None = None


def _get_limiter() -> _MemoryRateLimiter | _RedisRateLimiter:
    global _limiter
    if _limiter is not None:
        return _limiter
    backend = settings.RATE_LIMIT_BACKEND
    if backend == "redis" and settings.REDIS_URL:
        _limiter = _RedisRateLimiter(
            settings.RATE_LIMIT_REQUESTS,
            settings.RATE_LIMIT_WINDOW_SECONDS,
        )
    else:
        _limiter = _MemoryRateLimiter(
            settings.RATE_LIMIT_REQUESTS,
            float(settings.RATE_LIMIT_WINDOW_SECONDS),
        )
    return _limiter


def reset_rate_limiter() -> None:
    """Clear cached limiter (tests)."""
    global _limiter
    _limiter = None


async def rate_limit_middleware(
    request: RaftRequest, call_next: CallNext
) -> RawResponse:
    """Apply per-client request limits when enabled in settings."""
    if not settings.RATE_LIMIT_ENABLED:
        return await call_next(request)

    client_key = request.client_ip
    limiter = _get_limiter()
    allowed = limiter.allow(client_key)
    if inspect.isawaitable(allowed) or hasattr(allowed, "__await__"):
        allowed = await allowed

    if not allowed:
        raise HTTPException(
            status_code=429,
            message="Too Many Requests",
            errors=[f"Rate limit exceeded ({settings.RATE_LIMIT_REQUESTS} per "
                    f"{settings.RATE_LIMIT_WINDOW_SECONDS}s)."],
        )

    response = await call_next(request)
    response.headers.setdefault(
        "X-RateLimit-Limit",
        str(settings.RATE_LIMIT_REQUESTS),
    )
    response.headers.setdefault(
        "X-RateLimit-Window",
        str(settings.RATE_LIMIT_WINDOW_SECONDS),
    )
    return response
