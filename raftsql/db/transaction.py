"""
Transaction scoping via ContextVar — multi-database aware.

Each database alias tracks its own scoped connection independently, so you can
open transactions on multiple databases simultaneously without interference.

Async usage::

    from raftsql import atomic

    # Default database
    async with atomic() as tx:
        await Item.objects.acreate(name="Widget", price=9.99)
        await Order.objects.acreate(item_id=1, qty=2)

    # Named database
    async with atomic(using="analytics") as tx:
        await Event.objects.using("analytics").acreate(name="page_view")

    # Force rollback without raising (dry-run)
    async with atomic() as tx:
        result = await simulate_work()
        if dry_run:
            tx.set_rollback(True)

    # Nested — inner block uses a SAVEPOINT
    async with atomic() as outer:
        await Item.objects.acreate(...)
        async with atomic() as inner:
            await Order.objects.acreate(...)
            inner.set_rollback(True)   # only inner savepoint rolled back

Sync usage::

    from raftsql import atomic_sync

    with atomic_sync() as tx:
        Item.objects.create(name="Widget", price=9.99)

    with atomic_sync(using="analytics") as tx:
        Event.objects.using("analytics").create(name="page_view")
"""
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# ContextVars — store {alias: connection} maps so multiple databases can each
# have an independent scoped connection inside the same async/sync context.
# ---------------------------------------------------------------------------

_current_async_conns: ContextVar[Dict[str, Any]] = ContextVar(
    "_current_async_conns", default={}
)
_current_sync_conns: ContextVar[Dict[str, Any]] = ContextVar(
    "_current_sync_conns", default={}
)

# ---------------------------------------------------------------------------
# Backward-compatible aliases that manager.py's _use_*_conn() functions use.
# They now delegate to the dict-based vars above.
# ---------------------------------------------------------------------------

class _LegacyConnVar:
    """
    Thin shim that makes the old ``_current_async_conn`` / ``_current_sync_conn``
    single-connection ContextVar interface work via the new dict-based var.
    Only the ``get()`` method is needed by manager.py's helper functions.
    """
    def __init__(self, dict_var: ContextVar, alias: str = "default") -> None:
        self._var = dict_var
        self._alias = alias

    def get(self) -> Optional[Any]:
        return self._var.get().get(self._alias)


# These names are imported by orm/manager.py — keep them alive.
_current_async_conn = _LegacyConnVar(_current_async_conns, "default")
_current_sync_conn  = _LegacyConnVar(_current_sync_conns,  "default")


class _ForceRollback(Exception):
    """Internal sentinel raised when set_rollback(True) is used."""


class TransactionHandle:
    """
    Yielded by :func:`atomic` / :func:`atomic_sync`.

    Lets you mark a transaction for rollback on exit WITHOUT raising an
    exception — useful for dry-runs and soft-fail logic::

        async with raftsql.atomic() as tx:
            result = await simulate_complex_work()
            if dry_run:
                tx.set_rollback(True)   # DB unchanged; no exception
        return result
    """

    def __init__(self) -> None:
        self._do_rollback: bool = False

    def set_rollback(self, do_rollback: bool) -> None:
        """Mark this block to rollback (True) or commit (False) on exit."""
        self._do_rollback = do_rollback

    def get_rollback(self) -> bool:
        """Return True if this block will rollback on exit."""
        return self._do_rollback


def _resolve_cfg(using: str):
    """Return the Config for *using*, falling back to from_env() if setup() was not called."""
    import raftsql
    configs = raftsql._global_configs
    if configs:
        cfg = configs.get(using)
        if cfg is None:
            available = list(configs.keys())
            raise RuntimeError(
                f"Database alias '{using}' is not configured. "
                f"Available aliases: {available}"
            )
        return cfg
    # setup() not yet called — best-effort via environment variables
    from ..conf.config import Config
    return Config.from_env()


@asynccontextmanager
async def atomic(using: str = "default"):
    """
    Async transaction context manager. Yields a :class:`TransactionHandle`.

    *using* selects the database alias (default: ``"default"``).

    Outermost call for *using* opens a fresh connection, sets the alias slot in
    the ContextVar so all ORM calls within the block reuse the same connection,
    and commits on exit.  Nested calls on the **same** alias automatically use a
    PostgreSQL ``SAVEPOINT``.  Nested calls on **different** aliases open
    independent transactions.

    Example — two databases in one request::

        async with atomic() as tx_main:
            user = await User.objects.acreate(username="alice")
            async with atomic(using="analytics") as tx_an:
                await Event.objects.using("analytics").acreate(user_id=user.id)
    """
    from .async_connection import AsyncConnection

    cfg = _resolve_cfg(using)
    handle = TransactionHandle()
    existing_map = _current_async_conns.get()

    if using in existing_map:
        # Nested on the same alias — use a SAVEPOINT.
        existing_conn = existing_map[using]
        try:
            async with existing_conn.atomic():
                yield handle
                if handle.get_rollback():
                    raise _ForceRollback()
        except _ForceRollback:
            pass  # savepoint rolled back; outer transaction continues
        return

    # Outermost call for this alias — open a fresh connection.
    async with AsyncConnection(cfg) as conn:
        new_map = {**existing_map, using: conn}
        token = _current_async_conns.set(new_map)
        try:
            try:
                async with conn.atomic():
                    yield handle
                    if handle.get_rollback():
                        raise _ForceRollback()
            except _ForceRollback:
                pass
        finally:
            _current_async_conns.reset(token)


@contextmanager
def atomic_sync(using: str = "default"):
    """
    Sync transaction context manager. Yields a :class:`TransactionHandle`.

    *using* selects the database alias (default: ``"default"``).

    Identical semantics to :func:`atomic` but for synchronous code.

    Example — two databases::

        with atomic_sync() as tx_main:
            user = User.objects.create(username="bob")
            with atomic_sync(using="analytics") as tx_an:
                Event.objects.using("analytics").create(user_id=user.id)
    """
    from .connection import Connection

    cfg = _resolve_cfg(using)
    handle = TransactionHandle()
    existing_map = _current_sync_conns.get()

    if using in existing_map:
        # Nested on the same alias — use a SAVEPOINT.
        existing_conn = existing_map[using]
        try:
            with existing_conn.atomic():
                yield handle
                if handle.get_rollback():
                    raise _ForceRollback()
        except _ForceRollback:
            pass
        return

    # Outermost call for this alias — open a fresh connection.
    with Connection(cfg) as conn:
        new_map = {**existing_map, using: conn}
        token = _current_sync_conns.set(new_map)
        try:
            try:
                with conn.atomic():
                    yield handle
                    if handle.get_rollback():
                        raise _ForceRollback()
            except _ForceRollback:
                pass
        finally:
            _current_sync_conns.reset(token)
