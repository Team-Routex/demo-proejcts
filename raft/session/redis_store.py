"""
raft.session.redis_store
~~~~~~~~~~~~~~~~~~~~~~~~

Redis-backed session store (JSON values, TTL = ``SESSION_MAX_AGE``).
"""

from __future__ import annotations

import json
from typing import Any

from raft.config.settings import settings
from raft.redis.client import get_redis, redis_key


class RedisSessionStore:
    """Session store that persists data in Redis with TTL."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    def _redis(self) -> Any:
        return self._client if self._client is not None else get_redis()

    def _key(self, session_id: str) -> str:
        return redis_key("session:", session_id)

    async def exists(self, session_id: str) -> bool:
        res = self._redis().exists(self._key(session_id))
        if hasattr(res, "__await__"):
            res = await res
        return bool(res)

    async def get(self, session_id: str) -> dict[str, Any]:
        res = self._redis().get(self._key(session_id))
        if hasattr(res, "__await__"):
            res = await res
        raw = res
        if not raw:
            return {}
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    async def set(self, session_id: str, data: dict[str, Any]) -> None:
        if not data:
            await self.delete(session_id)
            return
        res = self._redis().set(
            self._key(session_id),
            json.dumps(data),
            ex=max(int(settings.SESSION_MAX_AGE), 1),
        )
        if hasattr(res, "__await__"):
            await res

    async def delete(self, session_id: str) -> None:
        res = self._redis().delete(self._key(session_id))
        if hasattr(res, "__await__"):
            await res
