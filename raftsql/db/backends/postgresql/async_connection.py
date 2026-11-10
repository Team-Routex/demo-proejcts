"""PostgreSQL async connection (asyncpg). Converts %s to $1,$2,... for asyncpg."""
import re
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, List, Optional, Sequence, Union

from ....conf.config import Config
from ..base import Backend


def _to_asyncpg_placeholders(sql: str) -> str:
    n = [0]
    def repl(_: Any) -> str:
        n[0] += 1
        return f"${n[0]}"
    return re.sub(r"%s", repl, sql)


class PostgreSQLAsyncConnection:
    """Async connection for PostgreSQL. Converts %s -> $1,$2 before execute."""

    def __init__(self, config: Config, backend: Backend):
        self._config = config
        self.backend = backend
        self._conn: Any = None
        self._pooled: bool = False   # True when conn was acquired from asyncpg pool

    async def open(self) -> "PostgreSQLAsyncConnection":
        if self._conn is not None:
            return self
        from ....db.pool import get_async_pool
        # Use the alias stored on the config for per-database pool lookup.
        alias = getattr(self._config, "alias", "default")
        pool = get_async_pool(alias)
        if pool is not None:
            self._conn = await pool.acquire()
            self._pooled = True
        else:
            import asyncpg
            self._conn = await asyncpg.connect(
                host=self._config.host,
                port=self._config.port,
                user=self._config.user,
                password=self._config.password,
                database=self._config.dbname,
            )
            self._pooled = False
        return self

    async def close(self) -> None:
        if self._conn is not None:
            if self._pooled:
                from ....db.pool import get_async_pool
                alias = getattr(self._config, "alias", "default")
                pool = get_async_pool(alias)
                if pool is not None:
                    await pool.release(self._conn)
            else:
                await self._conn.close()
            self._conn = None
            self._pooled = False

    async def _ensure_conn(self) -> Any:
        if self._conn is None:
            await self.open()
        return self._conn

    async def __aenter__(self) -> "PostgreSQLAsyncConnection":
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
        params = params or ()
        sql = _to_asyncpg_placeholders(sql)
        conn = await self._ensure_conn()
        rows = await conn.fetch(sql, *params)
        if as_dict:
            return [dict(r) for r in rows]
        return [tuple(r.values()) for r in rows]

    @asynccontextmanager
    async def atomic(self) -> AsyncGenerator[None, None]:
        """
        Async transaction context manager. Nested calls create savepoints
        automatically (asyncpg handles this internally via conn.transaction()).

        Usage:
            async with conn.atomic():
                await conn.execute(...)
                async with conn.atomic():  # savepoint
                    await conn.execute(...)
        """
        db_conn = await self._ensure_conn()
        async with db_conn.transaction():
            yield
