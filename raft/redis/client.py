"""
raft.redis.client
~~~~~~~~~~~~~~~~~

Redis configuration and lazy client access for Raft.

The ``redis`` package ships with Raft. Usage is opt-in via config only::

    RAFT_REDIS_URL=redis://localhost:6379/0
    RAFT_REDIS_PREFIX=raft:
    RAFT_SESSION_BACKEND=memory   # or ``redis`` when URL is set

Leave ``RAFT_REDIS_URL`` empty to skip Redis entirely.
"""

from __future__ import annotations

from typing import Any

import redis.asyncio as redis_async

from raft.config.settings import settings

_redis_client: Any | None = None


def redis_configured() -> bool:
    """True when a Redis URL is set (does not check connectivity)."""
    return bool(getattr(settings, "REDIS_URL", "") or "")


def get_redis(*, decode_responses: bool = True) -> Any:
    """Return a shared async Redis client (lazy singleton).

    Raises:
        RuntimeError: If ``RAFT_REDIS_URL`` is empty.
    """
    global _redis_client
    url = (settings.REDIS_URL or "").strip()
    if not url:
        raise RuntimeError(
            "Redis is not configured. Set RAFT_REDIS_URL "
            "(e.g. redis://localhost:6379/0)."
        )

    if _redis_client is None:
        _redis_client = redis_async.from_url(
            url,
            decode_responses=decode_responses,
        )
    return _redis_client


def reset_redis_client() -> None:
    """Drop the cached client (tests / reconnect)."""
    global _redis_client
    if _redis_client is not None:
        try:
            import asyncio

            close_func = getattr(_redis_client, "aclose", None) or getattr(_redis_client, "close", None)
            if close_func:
                res = close_func()
                if asyncio.iscoroutine(res):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(res)
                    except RuntimeError:
                        asyncio.run(res)
        except Exception:
            pass
    _redis_client = None


def redis_key(*parts: str) -> str:
    """Build a namespaced Redis key using ``RAFT_REDIS_PREFIX``."""
    prefix = settings.REDIS_PREFIX or "raft:"
    if not prefix.endswith(":") and parts:
        prefix = prefix + ":"
    return prefix + "".join(parts)
