"""
Async database connection. Dispatches to the backend for the given config.engine.
"""
from typing import Any, List, Optional, Sequence, Union

from .backends import get_backend
from ..conf.config import Config


class AsyncConnection:
    """
    Async connection. Uses config.engine to select backend; exposes .backend and .execute().
    Use as async context manager or call open/close.
    """

    def __init__(self, config: Optional[Config] = None):
        self._config = config or Config.from_env()
        self._backend = get_backend(self._config.engine)
        self._conn = self._backend.create_async_connection(self._config)

    @property
    def backend(self):
        return self._conn.backend

    async def open(self) -> "AsyncConnection":
        await self._conn.open()
        return self

    async def close(self) -> None:
        await self._conn.close()

    async def __aenter__(self) -> "AsyncConnection":
        await self.open()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def execute(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
        *,
        as_dict: bool = True,
    ) -> List[Union[tuple, dict]]:
        return await self._conn.execute(sql, params or (), as_dict=as_dict)

    def atomic(self):
        """Return an async transaction context manager (with savepoint support for nesting)."""
        return self._conn.atomic()
