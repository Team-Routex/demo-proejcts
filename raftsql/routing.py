"""
RaftSQL Database Guides — intelligent, model-aware database routing.

A Guide is a small class (or a pair of lambdas) that answers two questions:
  • *read*  → which database alias should SELECT queries for this model use?
  • *write* → which database alias should INSERT / UPDATE / DELETE use?

Return a string alias to claim the routing decision, or ``None`` to defer to
the next registered guide (or the default database if no guide claims it).

Multiple guides can be stacked with ``add_guide()``; the first non-``None``
answer wins.  Explicitly calling ``.using("alias")`` on a QuerySet bypasses
Meta, routers, and guides for that query.

----

Basic example — read replica + primary write::

    from raftsql.routing import Guide
    import raftsql

    class ReadReplicaGuide(Guide):
        def read(self, model, **hints):
            return "replica"       # all reads → replica DB

        def write(self, model, **hints):
            return "default"       # all writes → primary DB

    raftsql.add_guide(ReadReplicaGuide())

Per-model routing example::

    class AnalyticsGuide(Guide):
        ANALYTICS_MODELS = {"events", "page_views", "sessions"}

        def read(self, model, **hints):
            if model._table in self.ANALYTICS_MODELS:
                return "analytics"
            return None            # defer — not our concern

        def write(self, model, **hints):
            if model._table in self.ANALYTICS_MODELS:
                return "analytics"
            return None

    raftsql.add_guide(AnalyticsGuide())

App-prefix routing::

    class AppGuide(Guide):
        APP_PREFIX = "billing_"

        def read(self, model, **hints):
            return "billing" if model._table.startswith(self.APP_PREFIX) else None

        def write(self, model, **hints):
            return "billing" if model._table.startswith(self.APP_PREFIX) else None

    raftsql.add_guide(AppGuide())

Lambda shorthand (for simple cases)::

    # Every read → "replica", every write → "default"
    raftsql.add_guide(
        read=lambda model: "replica",
        write=lambda model: "default",
    )

    # Only route one specific table
    raftsql.add_guide(
        read=lambda model: "analytics" if model._table == "events" else None,
    )

Stacking multiple guides::

    raftsql.add_guide(AnalyticsGuide())    # handles analytics tables
    raftsql.add_guide(BillingGuide())      # handles billing tables
    raftsql.add_guide(FallbackGuide())     # catch-all for everything else

Guide order matters: guides are consulted in registration order.

Django-style DATABASE_ROUTERS
────────────────────────────────
Declare ``DATABASE_ROUTERS`` in ``setraft.py`` (same as Django).

Each router implements any subset of ``db_for_read``, ``db_for_write``,
``allow_relation``, ``allow_migrate``. Per model/operation, **``class Meta``**
(``db_alias``, ``for_read`` / ``for_write``, ``db_for_read`` / ``db_for_write``,
``allow_relation``, ``allow_migrate``, …) is checked **first** for DB routing; if
Meta supplies an alias for that half, ``DATABASE_ROUTERS`` and Guides are **not**
consulted for that half. Otherwise routers run, then Guides, then the queryset's
starter alias (usually ``"default"``).

``.using("alias")`` on a queryset bypasses Meta, routers, and guides.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


# ---------------------------------------------------------------------------
# Django-style DATABASE_ROUTERS
# ---------------------------------------------------------------------------


class BaseDatabaseRouter:
    """
    Stateless router skeleton — override the methods your app needs.

    Same contract as Django's ``DATABASE_ROUTERS`` entries::

        db_for_read(model, **hints)  → database alias string or ``None``
        db_for_write(model, **hints) → database alias string or ``None``
        allow_relation(obj1, obj2, **hints)
            ``True``  — relation is allowed;
            ``False`` — forbidden;
            ``None``  — defer to other routers / same-DB heuristic.
        allow_migrate(db, app_label, model_name=None, **hints)
            ``True`` — run app migrations on this database;
            ``False`` — skip;
            ``None``  — defer.
    """

    def db_for_read(self, model: "Any", **hints) -> Optional[str]:
        return None

    def db_for_write(self, model: "Any", **hints) -> Optional[str]:
        return None

    def allow_relation(self, obj1: "Any", obj2: "Any", **hints) -> Optional[bool]:
        return None

    def allow_migrate(self, db: str, app_label: str, model_name=None, **hints) -> Optional[bool]:
        return None


class _RouterEngine:
    def __init__(self) -> None:
        self._routers: List[Any] = []

    def clear(self) -> None:
        self._routers.clear()

    def add(self, router: Any) -> None:
        self._routers.append(router)

    @property
    def active(self) -> bool:
        return bool(self._routers)

    def db_for_read(self, model: "Any", **hints) -> Optional[str]:
        for r in self._routers:
            fn = getattr(r, "db_for_read", None)
            if fn is None:
                continue
            v = fn(model, **hints)
            if v is not None:
                return v
        return None

    def db_for_write(self, model: "Any", **hints) -> Optional[str]:
        for r in self._routers:
            fn = getattr(r, "db_for_write", None)
            if fn is None:
                continue
            v = fn(model, **hints)
            if v is not None:
                return v
        return None


_router_engine = _RouterEngine()


def allow_relation_allowed(obj1: "Any", obj2: "Any", **hints) -> bool:
    """
    Return True if a relation between *obj1* and *obj2* is allowed.

    Aggregates router ``allow_relation`` hooks (same idea as Django):
    • If **any** router returns ``False`` → not allowed.
    • Else if **any** returns ``True`` → allowed.
    • Else (all ``None``) → allowed when **Meta** does not forbid cross-DB
      (``allow_relation=False`` on either model and different write DB → deny),
      or **either** model sets ``allow_relation=True`` → allow; otherwise same
      **effective write** alias only.
    """
    cls1 = type(obj1)
    cls2 = type(obj2)
    saw_false = False
    saw_true = False
    for r in _router_engine._routers:
        fn = getattr(r, "allow_relation", None)
        if fn is None:
            continue
        v = fn(obj1, obj2, **hints)
        if v is False:
            saw_false = True
        elif v is True:
            saw_true = True
    if saw_false:
        return False
    if saw_true:
        return True
    w1 = resolve_default_database_alias(cls1, "write", starter="default")
    w2 = resolve_default_database_alias(cls2, "write", starter="default")

    m1 = getattr(cls1._meta, "allow_relation", None)
    m2 = getattr(cls2._meta, "allow_relation", None)
    if m1 is False or m2 is False:
        if w1 != w2:
            return False
    if m1 is True or m2 is True:
        return True
    return w1 == w2


def allow_migrate_allowed(
    db: str,
    app_label: str,
    model_name: Optional[str] = None,
    **hints,
) -> bool:
    """
    Return whether migrations for ``app_label`` should run against database alias *db*.

    Router aggregation (Django-style): explicit ``False`` wins; explicit ``True`` wins.

    Then **model ``Meta``**: any registered model with this ``app_label`` may veto
    via ``allow_migrate=False`` or ``allow_migrate_on_databases`` not containing *db*.
    """
    saw_false = saw_true = False
    for r in _router_engine._routers:
        fn = getattr(r, "allow_migrate", None)
        if fn is None:
            continue
        v = fn(db, app_label, model_name, **hints)
        if v is False:
            saw_false = True
        elif v is True:
            saw_true = True
    if saw_false:
        return False
    if saw_true:
        return True

    from raftsql.orm.model import get_registered_models_for_app_label

    for m in get_registered_models_for_app_label(app_label):
        meta = m._meta
        if getattr(meta, "allow_migrate", None) is False:
            return False
        allowed_only = getattr(meta, "allow_migrate_on_databases", None)
        if allowed_only is not None and db not in allowed_only:
            return False
    return True


def clear_database_routers() -> None:
    """Unregister all DATABASE_ROUTERS (testing / reload)."""
    _router_engine.clear()


def list_database_routers() -> List[Any]:
    """Return router instances registered on the router engine."""
    return list(_router_engine._routers)


# ---------------------------------------------------------------------------
# Guide base class
# ---------------------------------------------------------------------------

class Guide:
    """
    Base class for database routing guides.

    Subclass this and override :meth:`read` and/or :meth:`write`.
    Return the database alias string to claim the routing decision,
    or ``None`` to pass it to the next guide in the chain.

    Example::

        class MyGuide(Guide):
            def read(self, model, **hints):
                return "replica" if model._table == "articles" else None

            def write(self, model, **hints):
                return "default"
    """

    def read(self, model: "Any", **hints) -> Optional[str]:
        """
        Return the database alias for SELECT operations on *model*, or
        ``None`` to defer to the next guide / the default database.
        """
        return None

    def write(self, model: "Any", **hints) -> Optional[str]:
        """
        Return the database alias for INSERT / UPDATE / DELETE on *model*,
        or ``None`` to defer.
        """
        return None


# ---------------------------------------------------------------------------
# Internal: function-based guide wrapper
# ---------------------------------------------------------------------------

class _FunctionGuide(Guide):
    """
    Wraps plain callables passed to ``add_guide(read=..., write=...)``.
    Not part of the public API — use ``add_guide()`` instead.
    """

    def __init__(
        self,
        read_fn: Optional[Callable] = None,
        write_fn: Optional[Callable] = None,
    ) -> None:
        self._read_fn = read_fn
        self._write_fn = write_fn

    def read(self, model: "Any", **hints) -> Optional[str]:
        return self._read_fn(model, **hints) if self._read_fn else None

    def write(self, model: "Any", **hints) -> Optional[str]:
        return self._write_fn(model, **hints) if self._write_fn else None


# ---------------------------------------------------------------------------
# Guide engine — manages the guide registry and resolves aliases
# ---------------------------------------------------------------------------

class _GuideEngine:
    """
    Internal singleton that holds the list of registered guides and runs
    the resolution chain.  Access via the module-level functions below.
    """

    def __init__(self) -> None:
        self._guides: List[Guide] = []

    # ── registration ──────────────────────────────────────────────────────

    def add(self, guide: Guide) -> None:
        """Append *guide* to the resolution chain."""
        self._guides.append(guide)

    def remove(self, guide: Guide) -> None:
        """Remove *guide* from the chain (no-op if not present)."""
        try:
            self._guides.remove(guide)
        except ValueError:
            pass

    def clear(self) -> None:
        """Remove all registered guides (useful in tests)."""
        self._guides.clear()

    # ── resolution ────────────────────────────────────────────────────────

    @property
    def active(self) -> bool:
        """True if at least one guide is registered."""
        return bool(self._guides)

    def resolve_read(self, model: "Any", default: str = "default") -> str:
        """
        Ask each guide's ``read()`` in order.
        Return the first non-``None`` answer, or *default* if none claimed it.
        """
        for guide in self._guides:
            result = guide.read(model)
            if result is not None:
                return result
        return default

    def resolve_write(self, model: "Any", default: str = "default") -> str:
        """
        Ask each guide's ``write()`` in order.
        Return the first non-``None`` answer, or *default* if none claimed it.
        """
        for guide in self._guides:
            result = guide.write(model)
            if result is not None:
                return result
        return default

    def resolve(self, model: "Any", operation: str, default: str = "default") -> str:
        """
        Resolve *operation* (``"read"`` or ``"write"``) for *model*.
        Convenience wrapper around :meth:`resolve_read` / :meth:`resolve_write`.
        """
        if operation == "write":
            return self.resolve_write(model, default=default)
        return self.resolve_read(model, default=default)


# Module-level singleton — the only instance used by the ORM.
_engine = _GuideEngine()


def resolve_default_database_alias(
    model_cls: "Any",
    operation: str,
    *,
    starter: str = "default",
) -> str:
    """
    Effective database alias when the queryset did **not** call ``.using()``.

    Order:
      1. ``class Meta``: string ``db_for_read`` / ``db_for_write``, else ``db_alias``
         for each half when ``for_read`` / ``for_write`` are ``True`` (default when
         ``db_alias`` is set)
      2. ``DATABASE_ROUTERS`` … first non-``None``
      3. ``GUIDES`` / ``add_guide()`` … same
      4. ``starter`` (normally the queryset's base alias, typically ``"default"``)

    Passed to connection lookup in ``raftsql.setup()`` configs.
    """
    op = "write" if operation == "write" else "read"
    resolved = starter

    meta = getattr(model_cls, "_meta", None)
    if meta is not None:
        pick = meta.routed_database_alias(op)
        if pick:
            return pick

    router_matched = False
    if _router_engine.active:
        if op == "write":
            rp = _router_engine.db_for_write(model_cls)
        else:
            rp = _router_engine.db_for_read(model_cls)
        if rp is not None:
            resolved = rp
            router_matched = True

    if not router_matched and _engine.active:
        resolved = _engine.resolve(model_cls, op, default=resolved)

    return resolved


# ---------------------------------------------------------------------------
# Public API functions
# ---------------------------------------------------------------------------

def add_guide(
    guide: Optional[Guide] = None,
    *,
    read: Optional[Callable] = None,
    write: Optional[Callable] = None,
) -> Guide:
    """
    Register a database routing guide.

    **Class-based (full control):**

    Pass a :class:`Guide` subclass instance::

        raftsql.add_guide(ReadReplicaGuide())

    **Lambda / function-based (quick setup):**

    Pass ``read=`` and/or ``write=`` callables that accept a model class and
    return an alias string or ``None``::

        raftsql.add_guide(
            read=lambda model: "replica",
            write=lambda model: "default",
        )

        raftsql.add_guide(
            read=lambda model: "analytics" if model._table.startswith("event") else None,
        )

    Returns the registered :class:`Guide` instance (useful for later removal).

    Raises ``TypeError`` if neither a Guide instance nor at least one callable is given.
    """
    if guide is not None:
        if not isinstance(guide, Guide):
            raise TypeError(
                f"add_guide() expects a Guide instance, got {type(guide).__name__}. "
                "To use a callable, pass it as read= or write= keyword argument."
            )
        _engine.add(guide)
        return guide

    if read is None and write is None:
        raise TypeError(
            "add_guide() requires either a Guide instance as the first argument "
            "or at least one of read= / write= callables."
        )

    fn_guide = _FunctionGuide(read_fn=read, write_fn=write)
    _engine.add(fn_guide)
    return fn_guide


def remove_guide(guide: Guide) -> None:
    """
    Remove a previously registered guide from the chain.

    *guide* must be the same object returned by (or passed to) :func:`add_guide`::

        g = raftsql.add_guide(read=lambda m: "replica")
        # ... later ...
        raftsql.remove_guide(g)
    """
    _engine.remove(guide)


def clear_guides() -> None:
    """
    Remove **all** registered guides, reverting to default-database behaviour.
    Useful in tests or when resetting application state::

        raftsql.clear_guides()
    """
    _engine.clear()


def list_guides() -> List[Guide]:
    """
    Return a copy of the currently registered guides in resolution order.
    Useful for introspection and debugging::

        for g in raftsql.list_guides():
            print(type(g).__name__)
    """
    return list(_engine._guides)
