"""
Connection pool management for RaftSQL — multi-database aware.

Async pools : asyncpg.Pool           (one per database alias)
Sync pools  : psycopg2 ThreadedConnectionPool  (one per database alias)

Single-database usage (backward compatible)
───────────────────────────────────────────
    import raftsql

    @app.on_event("startup")
    async def startup():
        raftsql.setup()
        await raftsql.setup_async_pool()      # pools the "default" alias

    @app.on_event("shutdown")
    async def shutdown():
        await raftsql.teardown_async_pool()

Multi-database usage
────────────────────
    @app.on_event("startup")
    async def startup():
        raftsql.setup()
        await raftsql.setup_async_pool(using="default",   min_size=2, max_size=10)
        await raftsql.setup_async_pool(using="analytics", min_size=1, max_size=5)

    @app.on_event("shutdown")
    async def shutdown():
        await raftsql.teardown_all_async_pools()
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# ── global pool registries ────────────────────────────────────────────────────
# Keyed by database alias (e.g. "default", "analytics").

_async_pools: Dict[str, Any] = {}   # alias → asyncpg.Pool
_sync_pools:  Dict[str, Any] = {}   # alias → psycopg2.pool.ThreadedConnectionPool


# ── accessors ─────────────────────────────────────────────────────────────────

def get_async_pool(alias: str = "default") -> Optional[Any]:
    """Return the asyncpg pool for *alias*, or ``None`` if not initialised."""
    return _async_pools.get(alias)


def get_sync_pool(alias: str = "default") -> Optional[Any]:
    """Return the psycopg2 pool for *alias*, or ``None`` if not initialised."""
    return _sync_pools.get(alias)


# ── initialisation ────────────────────────────────────────────────────────────

async def initialize_async_pool(
    config: Any,
    *,
    alias: str = "default",
    min_size: int = 2,
    max_size: int = 10,
) -> None:
    """Create (or replace) an asyncpg connection pool for *alias*."""
    import asyncpg
    _async_pools[alias] = await asyncpg.create_pool(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.dbname,
        min_size=min_size,
        max_size=max_size,
    )


def initialize_sync_pool(
    config: Any,
    *,
    alias: str = "default",
    min_conn: int = 1,
    max_conn: int = 10,
) -> None:
    """Create (or replace) a psycopg2 ThreadedConnectionPool for *alias*."""
    import psycopg2.pool
    _sync_pools[alias] = psycopg2.pool.ThreadedConnectionPool(
        minconn=min_conn,
        maxconn=max_conn,
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        dbname=config.dbname,
    )


# ── teardown ──────────────────────────────────────────────────────────────────

async def close_async_pool(alias: str = "default") -> None:
    """Drain and close the asyncpg pool for *alias*."""
    pool = _async_pools.pop(alias, None)
    if pool is not None:
        await pool.close()


def close_sync_pool(alias: str = "default") -> None:
    """Close all psycopg2 pool connections for *alias*."""
    pool = _sync_pools.pop(alias, None)
    if pool is not None:
        pool.closeall()


# ── stats ─────────────────────────────────────────────────────────────────────

def pool_stats() -> dict:
    """
    Return pool statistics for every initialised alias.

    Example return value::

        {
            "default":   {"async": {"min_size": 2, "max_size": 10, "size": 3, "idle": 2},
                          "sync":  None},
            "analytics": {"async": None,
                          "sync":  {"min_conn": 1, "max_conn": 5, "closed": False}},
        }
    """
    all_aliases = set(_async_pools) | set(_sync_pools)
    stats: dict = {}

    for alias in all_aliases:
        entry: dict = {}

        async_pool = _async_pools.get(alias)
        if async_pool is not None:
            entry["async"] = {
                "min_size": async_pool.get_min_size(),
                "max_size": async_pool.get_max_size(),
                "size":     async_pool.get_size(),
                "idle":     async_pool.get_idle_size(),
            }
        else:
            entry["async"] = None

        sync_pool = _sync_pools.get(alias)
        if sync_pool is not None:
            entry["sync"] = {
                "min_conn": sync_pool.minconn,
                "max_conn": sync_pool.maxconn,
                "closed":   sync_pool.closed,
            }
        else:
            entry["sync"] = None

        stats[alias] = entry

    return stats
