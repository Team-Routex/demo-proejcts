"""
RaftSQL — Minimal ORM from scratch. PostgreSQL, sync + async, Django-like feel.
"""
__version__ = "1.1.0"

from .db.transaction import atomic, atomic_sync, TransactionHandle

# ---------------------------------------------------------------------------
# Global state set by setup()
# ---------------------------------------------------------------------------

# Multi-db: alias → Config  (populated by setup())
_global_configs: dict = {}

# Legacy single-db convenience pointer — always _global_configs.get("default")
_global_config = None

_media_root: str = "media"
_media_url:  str = "/media/"


def setup() -> None:
    """
    Configure raftsql by auto-discovering setraft.py in the project.

    RaftSQL searches for setraft.py starting from the current directory,
    walking upward to parent directories, then downward into subdirectories.

    Usage (in your main.py / app.py)::

        import raftsql
        raftsql.setup()

    **Single-database** setraft.py (backward-compatible)::

        DATABASE = {
            "ENGINE":   "postgresql",
            "HOST":     os.getenv("DB_HOST", "localhost"),
            "PORT":     int(os.getenv("DB_PORT", 5432)),
            "USER":     os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "NAME":     os.getenv("DB_NAME", "mydb"),
        }

    **Multi-database** setraft.py::

        DATABASES = {
            "default": {
                "ENGINE": "postgresql",
                "HOST": os.getenv("DB_HOST", "localhost"),
                "PORT": int(os.getenv("DB_PORT", 5432)),
                "USER": os.getenv("DB_USER", "postgres"),
                "PASSWORD": os.getenv("DB_PASSWORD", ""),
                "NAME": os.getenv("DB_NAME", "mydb"),
            },
            "analytics": {
                "ENGINE": "postgresql",
                "HOST": os.getenv("ANALYTICS_DB_HOST", "localhost"),
                "PORT": int(os.getenv("ANALYTICS_DB_PORT", 5432)),
                "USER": os.getenv("ANALYTICS_DB_USER", "postgres"),
                "PASSWORD": os.getenv("ANALYTICS_DB_PASSWORD", ""),
                "NAME": os.getenv("ANALYTICS_DB_NAME", "analytics"),
            },
        }
    """
    global _global_config, _global_configs, _media_root, _media_url
    if _global_configs:
        return  # already configured (safe for uvicorn --reload)

    from .conf.loader import (
        get_all_db_configs,
        get_media_config,
        get_database_routers,
        get_guides,
    )
    from .conf.config import Config

    all_dbs = get_all_db_configs()
    media = get_media_config()
    _media_root = media["MEDIA_ROOT"]
    _media_url  = media["MEDIA_URL"]

    for alias, db in all_dbs.items():
        _global_configs[alias] = Config(
            engine=db.get("ENGINE", "postgresql"),
            host=db.get("HOST", "localhost"),
            port=int(db.get("PORT", 5432)),
            user=db.get("USER", "postgres"),
            password=db.get("PASSWORD", ""),
            dbname=db.get("NAME", ""),
            media_root=_media_root,
            media_url=_media_url,
            alias=alias,
        )

    # Keep the legacy pointer alive for code that references _global_config directly
    _global_config = _global_configs.get("default")

    # DATABASE_ROUTERS (Django-style) then legacy GUIDES
    from .routing import _router_engine, _engine as _guide_engine

    _router_engine.clear()
    for router in get_database_routers():
        _router_engine.add(router)

    _guide_engine.clear()
    for guide in get_guides():
        _guide_engine.add(guide)


def get_db(alias: str = "default"):
    """
    Return the :class:`~raftsql.conf.config.Config` for the given database alias.

    Raises ``RuntimeError`` if ``setup()`` has not been called, or if the alias
    was not declared in ``DATABASES`` / ``DATABASE`` in ``setraft.py``::

        cfg = raftsql.get_db("analytics")
    """
    if not _global_configs:
        raise RuntimeError(
            "raftsql is not configured. Call raftsql.setup() first."
        )
    if alias not in _global_configs:
        available = list(_global_configs.keys())
        raise RuntimeError(
            f"Database alias '{alias}' is not configured. "
            f"Available aliases: {available}"
        )
    return _global_configs[alias]


# ── Public API ────────────────────────────────────────────────────────────────

# Configuration
from .conf.config import Config

# Connections
from .db.connection import Connection
from .db.async_connection import AsyncConnection

# ORM core
from .orm.model import Model
from .orm.manager import Manager, QuerySet
from .orm.queryset import NotFound, MultipleObjects

# Fields
from .orm.fields import (
    AutoField, IntegerField, BigIntegerField, FloatField, DecimalField,
    CharField, TextField, EmailField, BooleanField, DateField, DateTimeField,
    JSONField,
    # New field types
    UUIDField, TimeField, SmallIntegerField, PositiveIntegerField,
    SlugField, BinaryField, ArrayField,
    # File / image fields
    FileField, ImageField, FieldFile,
    # Relation fields
    ForeignKey, OneToOneField, ManyToManyField,
    CASCADE, SET_NULL, PROTECT, RESTRICT, DO_NOTHING,
)

# Query helpers
from .orm.q import Q
from .orm.f import F
from .orm.aggregates import Count, Sum, Avg, Max, Min

# Advanced expressions
from .orm.expressions import (
    Window,
    RowNumber, Rank, DenseRank, PercentRank, CumeDist, Ntile,
    Lag, Lead, FirstValue, LastValue, NthValue,
    Coalesce, Value,
    Subquery, OuterRef,
    Case, When,
    Cast,
)

# SQL builders
from .sql import build_insert, build_select, build_update

# Serializers
from .serializers import Serializer, ModelSerializer

# ── Connection pool helpers ───────────────────────────────────────────────────
from .db.pool import pool_stats


async def setup_async_pool(
    *,
    using: str = "default",
    min_size: int = 2,
    max_size: int = 10,
) -> None:
    """
    Initialise an asyncpg connection pool for the given database alias.
    Must be called *after* ``raftsql.setup()`` (so config is loaded).

    Single-database (default alias)::

        @app.on_event("startup")
        async def startup():
            raftsql.setup()
            await raftsql.setup_async_pool()

    Multi-database — call once per alias you want pooled::

        await raftsql.setup_async_pool(using="default",   min_size=2, max_size=10)
        await raftsql.setup_async_pool(using="analytics", min_size=1, max_size=5)
    """
    cfg = get_db(using)
    from .db.pool import initialize_async_pool
    await initialize_async_pool(cfg, alias=using, min_size=min_size, max_size=max_size)


async def teardown_async_pool(*, using: str = "default") -> None:
    """Close the asyncpg pool for the given alias. Call in ``@app.on_event("shutdown")``."""
    from .db.pool import close_async_pool
    await close_async_pool(alias=using)


async def teardown_all_async_pools() -> None:
    """Close asyncpg pools for **all** configured database aliases."""
    from .db.pool import close_async_pool
    for alias in list(_global_configs.keys()):
        await close_async_pool(alias=alias)


def setup_sync_pool(
    *,
    using: str = "default",
    min_conn: int = 1,
    max_conn: int = 10,
) -> None:
    """
    Initialise a psycopg2 ThreadedConnectionPool for the given database alias.
    Must be called *after* ``raftsql.setup()``.

    Multi-database::

        raftsql.setup_sync_pool(using="default",   min_conn=2, max_conn=10)
        raftsql.setup_sync_pool(using="analytics", min_conn=1, max_conn=5)
    """
    cfg = get_db(using)
    from .db.pool import initialize_sync_pool
    initialize_sync_pool(cfg, alias=using, min_conn=min_conn, max_conn=max_conn)


def teardown_sync_pool(*, using: str = "default") -> None:
    """Close psycopg2 pool connections for the given alias."""
    from .db.pool import close_sync_pool
    close_sync_pool(alias=using)


def teardown_all_sync_pools() -> None:
    """Close psycopg2 pools for **all** configured database aliases."""
    from .db.pool import close_sync_pool
    for alias in list(_global_configs.keys()):
        close_sync_pool(alias=alias)

# Signals
from .orm.signals import pre_save, post_save, pre_delete, post_delete, Signal

# Database routers + guides (``DATABASE_ROUTERS`` / ``GUIDES`` in setraft.py)
from .routing import (
    BaseDatabaseRouter,
    Guide,
    add_guide,
    allow_migrate_allowed,
    allow_relation_allowed,
    clear_database_routers,
    clear_guides,
    list_database_routers,
    list_guides,
    remove_guide,
    resolve_default_database_alias,
)

# Re-export models module for: from raftsql import models; models.CharField
from . import models
