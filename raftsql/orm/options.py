"""
Per-model metadata (Django-compatible ``_meta`` subset).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Tuple, Type

if TYPE_CHECKING:
    pass


def _meta_bool(attr: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"Meta.{attr} must be bool, not {type(value).__name__}")
    return value


def _optional_meta_bool(attr: str, value: Any) -> Optional[bool]:
    if value is None:
        return None
    return _meta_bool(attr, value)


def _optional_db_alias_tuple(name: str, value: Any) -> Optional[Tuple[str, ...]]:
    """``allow_migrate_on_databases`` — non-empty iterable of alias strings."""
    if value is None:
        return None
    if isinstance(value, (str, bytes)):
        raise TypeError(f"Meta.{name} must be a list/tuple of aliases, not a string")
    if not isinstance(value, (list, tuple)):
        raise TypeError(
            f"Meta.{name} must be a tuple or list of database alias strings or None, "
            f"not {type(value).__name__}"
        )
    out: list = []
    for x in value:
        s = str(x).strip()
        if not s:
            raise ValueError(f"Meta.{name} contains an empty alias string")
        out.append(s)
    return tuple(out)


def _optional_alias(name: str, value: Any) -> Optional[str]:
    """Normalise ``Meta.db_alias`` / ``db_for_read`` / ``db_for_write``."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(
            f'Meta.{name} must be str or None, not {type(value).__name__}'
        )
    s = value.strip()
    if not s:
        raise ValueError(f"Meta.{name} cannot be empty or whitespace-only")
    return s


def _derive_app_label(module: str) -> str:
    """
    Best-effort app label from ``Model.__module__``.

    ``apps.posts.models`` → ``posts``
    ``myapp.models`` → ``myapp``
    """
    parts = (module or "").split(".")
    if "models" in parts:
        i = parts.index("models")
        if i > 0:
            return parts[i - 1]
    if len(parts) >= 2:
        return parts[-2]
    return parts[0] if parts else "models"


class Options:
    """
    Attached to each model as ``Model._meta`` (Django-style).

    Attributes
    ----------
    app_label
        From ``class Meta: app_label = "..."`` if set, else derived from ``__module__``.
    model_name
        Lowercased class name (Django convention).
    label
        ``"{app_label}.{model_name}"`` — stable identifier for routing.
    db_table
        Physical table name for this model.
    db_alias
        If set, reads and writes can use this alias (subject to booleans ``for_read``
        / ``for_write``). String attrs ``db_for_read`` / ``db_for_write`` override
        this for their half regardless of ``for_*``. Must be a key in ``DATABASES``.
    for_read / for_write
        When ``db_alias`` is set: if ``True`` (default), that half uses
        ``db_alias``; if ``False``, defer that half to routers / Guides /
        ``"default"``. Ignored when ``db_alias`` is not set (string
        ``db_for_read`` / ``db_for_write`` still apply on their own).
    db_for_read / db_for_write
        Explicit alias strings for SELECT vs write half (override ``db_alias``
        ``for_*`` gates for that half).
    allow_relation
        ``False`` → forbid FK links when the two models land on **different**
        effective write aliases; ``True`` → allow cross-database relations
        involving this model (unless a router forbids); ``None`` → defer to
        router outcome + same-write-DB heuristic.
    allow_migrate
        ``False`` → disallow running migrations for this model's ``app_label`` on
        any database (applied after routers; see also ``allow_migrate_on_databases``).
        ``None`` → no veto from this flag.
    allow_migrate_on_databases
        If set, migrations for ``app_label`` are **not** run on aliases **outside**
        this list (union of vetoes across all models registered for ``app_label``).

    Models with **none** of ``db_alias`` / ``db_for_read`` / ``db_for_write`` use the
    global ``"default"`` starter alias unless ``DATABASE_ROUTERS`` / Guides
    redirect — same as Django's implicit default DB when multi-db is enabled.

    When :meth:`routed_database_alias` returns a string, that alias is used and
        ``DATABASE_ROUTERS`` / Guides are **not** consulted for that half. When it
        returns ``None``, routers and Guides run; resolution ends on the queryset
        starter (usually ``"default"``) when nothing else picks an alias.

    """

    def __init__(self, model_cls: Type[Any], meta: Optional[Any]) -> None:
        self.db_table: str = model_cls._get_table()
        self.model_name: str = model_cls.__name__.lower()
        explicit = getattr(meta, "app_label", None) if meta is not None else None
        self.app_label: str = explicit or _derive_app_label(
            getattr(model_cls, "__module__", "") or ""
        )
        self.label: str = f"{self.app_label}.{self.model_name}"
        self.db_alias: Optional[str] = None
        self.db_for_read: Optional[str] = None
        self.db_for_write: Optional[str] = None
        self.use_db_alias_for_read: bool = True
        self.use_db_alias_for_write: bool = True
        self.allow_relation: Optional[bool] = None
        self.allow_migrate: Optional[bool] = None
        self.allow_migrate_on_databases: Optional[Tuple[str, ...]] = None
        if meta is not None:
            self.db_alias = _optional_alias("db_alias", getattr(meta, "db_alias", None))
            self.db_for_read = _optional_alias(
                "db_for_read", getattr(meta, "db_for_read", None)
            )
            self.db_for_write = _optional_alias(
                "db_for_write", getattr(meta, "db_for_write", None)
            )
            if self.db_alias is not None:
                fr = getattr(meta, "for_read", None)
                if fr is not None:
                    self.use_db_alias_for_read = _meta_bool("for_read", fr)
                fw = getattr(meta, "for_write", None)
                if fw is not None:
                    self.use_db_alias_for_write = _meta_bool("for_write", fw)
            self.allow_relation = _optional_meta_bool(
                "allow_relation", getattr(meta, "allow_relation", None)
            )
            self.allow_migrate = _optional_meta_bool(
                "allow_migrate", getattr(meta, "allow_migrate", None)
            )
            self.allow_migrate_on_databases = _optional_db_alias_tuple(
                "allow_migrate_on_databases",
                getattr(meta, "allow_migrate_on_databases", None),
            )

    def routed_database_alias(self, operation: str) -> Optional[str]:
        """
        Explicit database alias from Meta for *operation* ("read" | "write"),
        or ``None`` to fall back to ``DATABASE_ROUTERS`` / Guides.

        Precedence per half: string ``db_for_read`` / ``db_for_write``, else
        ``db_alias`` when the corresponding ``for_read`` / ``for_write`` flag
        is ``True`` (defaults ``True`` when ``db_alias`` is set).
        """
        op = "write" if operation == "write" else "read"
        if op == "write":
            if self.db_for_write is not None:
                return self.db_for_write
            if self.db_alias is not None and self.use_db_alias_for_write:
                return self.db_alias
            return None
        if self.db_for_read is not None:
            return self.db_for_read
        if self.db_alias is not None and self.use_db_alias_for_read:
            return self.db_alias
        return None

    def __repr__(self) -> str:
        return f"<Options for {self.label}>"
