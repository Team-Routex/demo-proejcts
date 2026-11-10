"""
Django-like Manager and QuerySet.

Supported QuerySet API
─────────────────────
Filtering
  .filter(*Q, **kwargs)          — AND conditions, supports lookups (price__gt=10)
  .exclude(*Q, **kwargs)         — negate conditions
  .filter(Q(...) | Q(...))       — OR via Q objects
  .filter(field__in=[1,2,3])
  .filter(field__isnull=True)
  .filter(field__icontains="foo")
  .filter(field__range=(1, 100))
  .filter(views__gt=F("likes"))  — column vs column

Shaping
  .order_by("name", "-created_at")
  .limit(n)  /  .offset(n)
  .distinct()
  .values("id", "name")          — return dicts
  .values_list("id", "name")     — return tuples
  .values_list("id", flat=True)  — return flat list

Relations
  .select_related("author")      — JOIN FK / O2O in one query
  .prefetch_related("tags")      — batch-fetch M2M after main query

Aggregation
  .aggregate(total=Sum("price"), count=Count("id"))   — returns dict
  .annotate(total=Sum("price"))                        — adds column per row
  .count()

Execution (sync)
  .all()    .first()   .get(**kw)   .create(**kw)
  .update(**kw)   .delete()   .exists()
  .raw(sql, params)     — run raw SQL, returns model instances

Execution (async)
  .alist()  .afirst()  .aget(**kw)  .acreate(**kw)
  .aupdate(**kw)  .adelete()  .aexists()  .acount()
  .aaggregate(**kw)
"""
from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .model import Model


# ── connection-scope helpers ─────────────────────────────────────────────────
# Each query method calls these instead of opening a raw Connection directly.
# When inside atomic() / atomic_sync() the ContextVar map is checked first;
# a matching scoped connection is reused, otherwise a fresh one is opened.

@asynccontextmanager
async def _use_async_conn(cfg):
    from ..db.transaction import _current_async_conns
    from ..db.async_connection import AsyncConnection
    alias = getattr(cfg, "alias", "default")
    scoped = _current_async_conns.get().get(alias)
    if scoped is not None:
        yield scoped
    else:
        async with AsyncConnection(cfg) as conn:
            yield conn


@contextmanager
def _use_sync_conn(cfg):
    from ..db.transaction import _current_sync_conns
    from ..db.connection import Connection
    alias = getattr(cfg, "alias", "default")
    scoped = _current_sync_conns.get().get(alias)
    if scoped is not None:
        yield scoped
    else:
        with Connection(cfg) as conn:
            yield conn


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_config(alias: str = "default", *, model=None, operation: str = "read"):
    """
    Resolve the Config to use for *alias* + *operation*.

    Delegates to ``raftsql.routing.resolve_default_database_alias`` when *model*
    is set.

    When *model* is ``None`` (raw SQL paths, explicit ``.using()`` override),
    *alias* is used as-is with no routing.
    """
    import raftsql
    from raftsql.routing import resolve_default_database_alias

    configs = raftsql._global_configs
    resolved = alias
    if model is not None:
        resolved = resolve_default_database_alias(model, operation, starter=alias)

    if configs:
        cfg = configs.get(resolved)
        if cfg is None:
            available = list(configs.keys())
            raise RuntimeError(
                f"Database alias '{resolved}' is not configured. "
                f"Available aliases: {available}"
            )
        return cfg

    # Legacy: _global_configs not yet populated (pre-setup() path)
    cfg = raftsql._global_config
    if cfg is None:
        raise RuntimeError(
            "raftsql is not configured. Call raftsql.setup() first."
        )
    return cfg


def _assert_foreign_object_relations_allowed(instance: Any) -> None:
    """
    If related model instances are attached (lazy FK caches), enforce
    ``DATABASE_ROUTERS.allow_relation`` aggregation before save().
    """
    from raftsql.routing import allow_relation_allowed

    cls = instance.__class__
    for attr_name in cls._relations:
        cached = instance.__dict__.get(f"_related_{attr_name}")
        if cached is None:
            continue
        peer_cls = getattr(cached, "__class__", type(None))
        if peer_cls.__name__ == "RelatedAccessor":
            continue
        if getattr(peer_cls, "_meta", None) is None:
            continue
        if not allow_relation_allowed(instance, cached):
            raise ValueError(
                "Cross-database relation is not permitted between "
                f"{cls.__name__} and {peer_cls.__name__} ({attr_name=}): "
                "database routers disallowed this link."
            )


def _wrap_kwargs_as_q(**kwargs) -> "Q | None":
    from .q import Q
    return Q(**kwargs) if kwargs else None


def _resolve_pk(model_class: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Translate 'pk' to the actual primary-key column name."""
    if "pk" in kwargs:
        pk_col = model_class._get_pk_column()
        kwargs = {**kwargs}
        kwargs[pk_col] = kwargs.pop("pk")
    return kwargs


# ── QuerySet ─────────────────────────────────────────────────────────────────

class QuerySet:
    """
    Lazy, chainable query builder.
    No SQL is issued until an execution method is called (.all(), .alist(), etc.)
    """

    def __init__(self, model_class: Any) -> None:
        self._model = model_class

        # Database alias — select which database this QuerySet targets.
        # _using_explicit is True only when .using() was called directly by the
        # caller; when False the guide engine is allowed to override the alias.
        self._using: str = "default"
        self._using_explicit: bool = False

        # WHERE nodes — list of Q objects, top-level ANDed
        self._where_nodes: List[Any] = []

        # Shaping
        self._order_by: List[str] = []
        self._limit_val: Optional[int] = None
        self._offset_val: Optional[int] = None
        self._distinct_val: bool = False

        # Output format
        self._values_fields: Optional[Tuple[str, ...]] = None   # values()
        self._values_list_fields: Optional[Tuple[str, ...]] = None  # values_list()
        self._flat: bool = False

        # Relations
        self._select_related_fields: List[str] = []
        self._prefetch_related_fields: List[str] = []

        # Annotations:  {alias: Aggregate | F}
        self._annotations: Dict[str, Any] = {}

        # Row locking
        self._for_update: bool = False

        # HAVING
        self._having_nodes: List[Any] = []

        # Partial field loading
        self._only_fields: Optional[Tuple[str, ...]] = None   # only() — include these
        self._defer_fields: Tuple[str, ...] = ()              # defer() — exclude these

    # ── clone helper ────────────────────────────────────────────────────────

    def _clone(self) -> "QuerySet":
        qs = QuerySet.__new__(QuerySet)
        qs._model = self._model
        qs._using = self._using
        qs._using_explicit = self._using_explicit
        qs._where_nodes = list(self._where_nodes)
        qs._order_by = list(self._order_by)
        qs._limit_val = self._limit_val
        qs._offset_val = self._offset_val
        qs._distinct_val = self._distinct_val
        qs._values_fields = self._values_fields
        qs._values_list_fields = self._values_list_fields
        qs._flat = self._flat
        qs._select_related_fields = list(self._select_related_fields)
        qs._prefetch_related_fields = list(self._prefetch_related_fields)
        qs._annotations = dict(self._annotations)
        qs._for_update = self._for_update
        qs._having_nodes = list(self._having_nodes)
        qs._only_fields = self._only_fields
        qs._defer_fields = self._defer_fields
        return qs

    # ── chaining (no DB call) ───────────────────────────────────────────────

    def using(self, alias: str) -> "QuerySet":
        """
        Select which database alias this QuerySet will execute against.

        Mirrors Django's ``.using()`` API::

            # Read from the "analytics" replica
            reports = Report.objects.using("analytics").filter(published=True).all()

            # Write to the default database
            Report.objects.using("default").create(title="Q1 Results")

        The alias must match a key in ``DATABASES`` (or ``"default"`` for the
        single-database ``DATABASE`` style) in ``setraft.py``.

        Calling ``.using()`` explicitly bypasses model ``Meta`` routing,
        ``DATABASE_ROUTERS``, and Guides for this QuerySet — the alias you
        provide is always used as-is.
        """
        qs = self._clone()
        qs._using = alias
        qs._using_explicit = True   # skip guide engine for this QuerySet
        return qs

    def filter(self, *q_objects, **kwargs) -> "QuerySet":
        """Add AND conditions. Supports Q objects and lookup kwargs."""
        from .q import Q
        qs = self._clone()
        kwargs = _resolve_pk(self._model, kwargs)
        if kwargs:
            qs._where_nodes.append(Q(**kwargs))
        for q in q_objects:
            qs._where_nodes.append(q)
        return qs

    def exclude(self, *q_objects, **kwargs) -> "QuerySet":
        """Add negated AND conditions (NOT ...)."""
        from .q import Q
        qs = self._clone()
        kwargs = _resolve_pk(self._model, kwargs)
        nodes = list(q_objects)
        if kwargs:
            nodes.append(Q(**kwargs))
        for node in nodes:
            qs._where_nodes.append(~node)
        return qs

    def order_by(self, *fields: str) -> "QuerySet":
        """ORDER BY. Prefix field with '-' for DESC."""
        qs = self._clone()
        qs._order_by = list(fields)
        return qs

    def limit(self, n: int) -> "QuerySet":
        qs = self._clone()
        qs._limit_val = n
        return qs

    def offset(self, n: int) -> "QuerySet":
        qs = self._clone()
        qs._offset_val = n
        return qs

    def distinct(self) -> "QuerySet":
        qs = self._clone()
        qs._distinct_val = True
        return qs

    def values(self, *fields: str) -> "QuerySet":
        """Return dicts instead of model instances."""
        qs = self._clone()
        qs._values_fields = fields if fields else tuple(self._model._get_columns())
        qs._values_list_fields = None
        return qs

    def values_list(self, *fields: str, flat: bool = False) -> "QuerySet":
        """Return tuples (or flat list if flat=True with a single field)."""
        if flat and len(fields) != 1:
            raise ValueError("flat=True requires exactly one field.")
        qs = self._clone()
        qs._values_list_fields = fields if fields else tuple(self._model._get_columns())
        qs._values_fields = None
        qs._flat = flat
        return qs

    def select_related(self, *fields: str) -> "QuerySet":
        """JOIN FK/O2O related objects in a single query."""
        qs = self._clone()
        qs._select_related_fields = list(fields)
        return qs

    def prefetch_related(self, *fields: str) -> "QuerySet":
        """Batch-fetch M2M / reverse-FK related objects in separate queries."""
        qs = self._clone()
        qs._prefetch_related_fields = list(fields)
        return qs

    def annotate(self, **kwargs) -> "QuerySet":
        """
        Add computed columns.

            Item.objects.values("category").annotate(total=Sum("price"))
            # SELECT category, SUM(price) AS total … GROUP BY category

            User.objects.annotate(post_count=Count("id"))
            # SELECT *, COUNT("id") AS post_count …
        """
        qs = self._clone()
        qs._annotations.update(kwargs)
        return qs

    def select_for_update(self) -> "QuerySet":
        """
        Lock selected rows with SELECT … FOR UPDATE.
        Must be used inside an atomic() / atomic_sync() block.

            with raftsql.atomic_sync():
                item = Item.objects.filter(pk=1).select_for_update().get(pk=1)
                item_update logic …
        """
        qs = self._clone()
        qs._for_update = True
        return qs

    def only(self, *fields: str) -> "QuerySet":
        """
        Load *only* the given fields (plus the pk).  All other columns are
        omitted from the SELECT.  Useful when you need one or two columns
        from a wide table.

            items = Item.objects.only("id", "name").all()
        """
        qs = self._clone()
        qs._only_fields = fields
        qs._defer_fields = ()
        return qs

    def defer(self, *fields: str) -> "QuerySet":
        """
        Load all fields *except* the given ones.  Handy for skipping heavy
        columns (e.g. large BLOBs) you don't need.

            items = Item.objects.defer("description").all()
        """
        qs = self._clone()
        qs._defer_fields = fields
        qs._only_fields = None
        return qs

    def having(self, *q_objects, **kwargs) -> "QuerySet":
        """
        Add HAVING conditions (filter on aggregated values).
        Must be combined with .values() + .annotate() (i.e. GROUP BY must be present).

            Item.objects\
                .values("in_stock")\
                .annotate(total=Count("id"))\
                .having(total__gte=3)\
                .all()
            # SELECT in_stock, COUNT(id) AS total
            # FROM items GROUP BY in_stock HAVING COUNT(id) >= 3
        """
        from .q import Q
        qs = self._clone()
        if kwargs:
            qs._having_nodes.append(Q(**kwargs))
        for q_obj in q_objects:
            qs._having_nodes.append(q_obj)
        return qs

    # ── config resolution helpers ────────────────────────────────────────────

    def _cfg_read(self):
        """Config for SELECT — applies Meta / routers / Guides unless .using() was explicit."""
        model = None if self._using_explicit else self._model
        return _get_config(self._using, model=model, operation="read")

    def _cfg_write(self):
        """Config for INSERT/UPDATE/DELETE — applies Meta / routers / Guides unless .using() was explicit."""
        model = None if self._using_explicit else self._model
        return _get_config(self._using, model=model, operation="write")

    # ── SQL construction ────────────────────────────────────────────────────

    def _build_where(self, backend, outer_table: Optional[str] = None, table: Optional[str] = None) -> Tuple[str, List]:
        from ..sql.where import build_where
        return build_where(self._where_nodes, backend, outer_table=outer_table, table=table)

    def _build_having(self, backend) -> Tuple[str, List]:
        """Build HAVING clause from _having_nodes.

        PostgreSQL does not allow SELECT-level aliases in HAVING, so we resolve
        annotation aliases to their underlying SQL expression before building.
        E.g. ``total__gte=3`` where ``total`` is ``Count("id")`` becomes
        ``COUNT("id") >= 3`` rather than ``"total" >= 3``.
        """
        from ..sql.where import build_where
        from .aggregates import Aggregate

        having_sql, having_params = build_where(self._having_nodes, backend)

        # Replace quoted annotation alias identifiers with their expression SQL.
        q = backend.quote_ident
        for alias, expr in self._annotations.items():
            quoted = q(alias)
            if quoted not in having_sql:
                continue
            if isinstance(expr, Aggregate):
                having_sql = having_sql.replace(quoted, expr.as_sql(backend))
            elif hasattr(expr, "as_sql"):
                import inspect as _inspect
                sig = _inspect.signature(expr.as_sql)
                if "params" not in sig.parameters:
                    having_sql = having_sql.replace(quoted, expr.as_sql(backend))
                # expressions that need params are left as-is (edge case)

        return having_sql, having_params


    def _build_select_sql(self, backend, outer_table: Optional[str] = None) -> Tuple[str, List]:
        """Build the full SELECT SQL and params for the current QuerySet state."""
        from ..sql.builder import build_select
        from .aggregates import Aggregate
        from .f import F
        from .expressions import Window, WindowFunction, Coalesce, Subquery

        table = self._model._get_table()
        q = backend.quote_ident

        # Determine which columns to SELECT.
        # Exclude annotation aliases — those come from extra_selects, not the table.
        annotation_aliases = set(self._annotations.keys())
        if self._values_fields is not None:
            columns = [f for f in self._values_fields if f not in annotation_aliases]
        elif self._values_list_fields is not None:
            columns = [f for f in self._values_list_fields if f not in annotation_aliases]
        else:
            base_cols = self._model._get_columns()
            if self._only_fields is not None:
                # Always include pk so instances are identifiable
                pk_col = self._model._get_pk_column()
                only_set = set(self._only_fields) | {pk_col}
                columns = [c for c in base_cols if c in only_set]
            elif self._defer_fields:
                defer_set = set(self._defer_fields)
                columns = [c for c in base_cols if c not in defer_set]
            else:
                columns = base_cols

        # Build annotation expressions
        # annotation_params holds params for SELECT-level expressions (Subquery, Coalesce+Value)
        annotation_params: List = []
        extra_selects: List[Tuple[str, str]] = []

        for alias, expr in self._annotations.items():
            if isinstance(expr, (Window, WindowFunction)):
                extra_selects.append((expr.as_sql(backend), alias))
            elif isinstance(expr, Aggregate):
                extra_selects.append((expr.as_sql(backend), alias))
            elif isinstance(expr, Coalesce):
                extra_selects.append((expr.as_sql(backend, annotation_params), alias))
            elif isinstance(expr, Subquery):
                resolved = expr.resolve(table)
                extra_selects.append((resolved.as_sql(backend, annotation_params), alias))
            elif isinstance(expr, F):
                extra_selects.append((q(expr.field), alias))
            else:
                # Case, Cast, and any expression with as_sql(backend, params)
                if hasattr(expr, "as_sql"):
                    import inspect
                    sig = inspect.signature(expr.as_sql)
                    if "params" in sig.parameters:
                        extra_selects.append((expr.as_sql(backend, annotation_params), alias))
                    else:
                        extra_selects.append((expr.as_sql(backend), alias))
                else:
                    extra_selects.append((str(expr), alias))

        # GROUP BY: when values() + annotate(), group by the values columns
        group_by: Optional[List[str]] = None
        if self._annotations and (self._values_fields is not None or self._values_list_fields is not None):
            group_by = list(self._values_fields or self._values_list_fields or [])

        # JOIN clauses for select_related
        joins: List[str] = []
        sr_columns: List[Tuple[str, str]] = []
        if self._select_related_fields:
            joins, sr_columns = self._build_joins(backend)
            extra_selects.extend(sr_columns)

        # MTI: auto-JOIN parent table so parent fields are accessible
        if getattr(self._model, "_parent_model", None) is not None:
            parent_model = self._model._parent_model
            parent_table = parent_model._get_table()
            parent_pk = parent_model._get_pk_column()
            ptr_col = self._model._ptr_col
            mti_join = (
                f"INNER JOIN {q(parent_table)} "
                f"ON {q(table)}.{q(ptr_col)} = {q(parent_table)}.{q(parent_pk)}"
            )
            joins.insert(0, mti_join)
            # Add parent columns (excluding parent PK) to extra_selects
            parent_cols = [c for c in parent_model._fields if c != parent_pk]
            parent_extra = [(f"{q(parent_table)}.{q(c)}", c) for c in parent_cols]
            extra_selects = parent_extra + extra_selects

        # Qualify WHERE columns with base table when JOINs are present to avoid
        # "ambiguous column reference" errors (e.g. "id" exists in multiple joined tables)
        where_table = table if joins else None
        where_sql, where_params = self._build_where(backend, outer_table=outer_table, table=where_table)

        # HAVING
        having_sql: Optional[str] = None
        having_params: Optional[List] = None
        if self._having_nodes:
            having_sql, having_params = self._build_having(backend)

        sql, params = build_select(
            backend,
            table,
            columns,
            where_sql=where_sql or None,
            where_params=where_params or None,
            extra_select_params=annotation_params or None,
            joins=joins or None,
            extra_selects=extra_selects or None,
            group_by=group_by,
            having_sql=having_sql,
            having_params=having_params,
            order_by=self._order_by or None,
            limit=self._limit_val,
            offset=self._offset_val,
            distinct=self._distinct_val,
            for_update=self._for_update,
        )
        return sql, params

    def _build_joins(self, backend) -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        Build LEFT JOIN clauses for select_related fields.
        Returns (join_clauses, extra_select_pairs).
        extra_select_pairs: (sql_expression, alias)
        """
        q = backend.quote_ident
        table = self._model._get_table()
        joins: List[str] = []
        extra_selects: List[Tuple[str, str]] = []

        relations = self._model._relations  # {attr_name: {"column": col, "to": Model}}

        for attr in self._select_related_fields:
            if attr not in relations:
                continue
            rel = relations[attr]
            fk_col = rel["column"]       # e.g. "author_id"
            related_model = rel["to"]
            related_table = related_model._get_table()
            related_pk = related_model._get_pk_column()
            related_cols = related_model._get_columns()

            # e.g. LEFT JOIN "users" AS _sr_author ON _sr_author."id" = "posts"."author_id"
            alias = f"_sr_{attr}"
            join = (
                f"LEFT JOIN {q(related_table)} AS {alias} "
                f"ON {alias}.{q(related_pk)} = {q(table)}.{q(fk_col)}"
            )
            joins.append(join)

            # Add each related column as an aliased extra select
            for col in related_cols:
                sql_expr = f"{alias}.{q(col)}"
                col_alias = f"_sr_{attr}__{col}"
                extra_selects.append((sql_expr, col_alias))

        return joins, extra_selects

    def _rows_to_instances(self, rows: List[Dict]) -> List[Any]:
        """Convert raw row dicts to model instances, attaching select_related objects."""
        instances = []
        for row in rows:
            # Extract select_related sub-dicts
            sr_data: Dict[str, Dict] = {}
            main_row: Dict = {}
            for key, val in row.items():
                if key.startswith("_sr_") and "__" in key[4:]:
                    # key like "_sr_author__name"
                    rest = key[4:]  # "author__name"
                    attr, col = rest.split("__", 1)
                    sr_data.setdefault(attr, {})[col] = val
                else:
                    main_row[key] = val

            instance = self._model.from_row(main_row)

            # Attach related instances into the cache so ForeignKey.__get__ returns them
            for attr, rel_row in sr_data.items():
                rel_model = self._model._relations[attr]["to"]
                rel_instance = rel_model.from_row(rel_row)
                object.__setattr__(instance, f"_related_{attr}", rel_instance)

            instances.append(instance)
        return instances

    def _apply_prefetch(self, instances: List[Any]) -> None:
        """Execute prefetch_related queries and attach results to instances."""
        if not instances or not self._prefetch_related_fields:
            return

        from ..db.connection import Connection
        from ..sql.builder import build_select

        cfg = self._cfg_read()
        pk_col = self._model._get_pk_column()
        pk_values = [getattr(inst, pk_col, None) for inst in instances]
        pk_values = [v for v in pk_values if v is not None]

        for attr in self._prefetch_related_fields:
            # M2M
            if attr in self._model._m2m:
                m2m_field = self._model._m2m[attr]
                related_model = m2m_field.to
                src_table = self._model._get_table()
                dst_table = related_model._get_table()
                junction = m2m_field.get_junction_table(src_table, dst_table)
                src_col = f"{src_table}_id"
                dst_col = f"{dst_table}_id"
                related_pk = related_model._get_pk_column()
                related_cols = related_model._get_columns()

                # SELECT related.*, junction.src_col AS _prefetch_src_id FROM related
                # JOIN junction ON junction.dst_col = related.pk
                # WHERE junction.src_col IN (...)
                q_fn = lambda x: f'"{x}"'  # simple quoting for raw SQL
                cols_expr = ", ".join(f"{q_fn(dst_table)}.{q_fn(c)}" for c in related_cols)
                placeholders = ", ".join(["%s"] * len(pk_values))
                sql = (
                    f'SELECT {cols_expr}, {q_fn(junction)}.{q_fn(src_col)} AS _prefetch_src_id'
                    f' FROM {q_fn(dst_table)}'
                    f' JOIN {q_fn(junction)} ON {q_fn(junction)}.{q_fn(dst_col)} = {q_fn(dst_table)}.{q_fn(related_pk)}'
                    f' WHERE {q_fn(junction)}.{q_fn(src_col)} IN ({placeholders})'
                )
                with Connection(cfg) as conn:
                    rows = conn.execute(sql, pk_values, as_dict=True)

                # Group by source id
                grouped: Dict[Any, List] = {}
                for row in rows:
                    row = dict(row)
                    src_id = row.pop("_prefetch_src_id")
                    grouped.setdefault(src_id, []).append(related_model.from_row(row))

                # Attach
                for inst in instances:
                    src_id = getattr(inst, pk_col, None)
                    object.__setattr__(inst, f"_prefetched_{attr}", grouped.get(src_id, []))

    async def _apply_prefetch_async(self, instances: List[Any]) -> None:
        """Async version of prefetch_related."""
        if not instances or not self._prefetch_related_fields:
            return

        from ..db.async_connection import AsyncConnection

        cfg = self._cfg_read()
        pk_col = self._model._get_pk_column()
        pk_values = [getattr(inst, pk_col, None) for inst in instances]
        pk_values = [v for v in pk_values if v is not None]

        for attr in self._prefetch_related_fields:
            if attr in self._model._m2m:
                m2m_field = self._model._m2m[attr]
                related_model = m2m_field.to
                src_table = self._model._get_table()
                dst_table = related_model._get_table()
                junction = m2m_field.get_junction_table(src_table, dst_table)
                src_col = f"{src_table}_id"
                dst_col = f"{dst_table}_id"
                related_pk = related_model._get_pk_column()
                related_cols = related_model._get_columns()

                q_fn = lambda x: f'"{x}"'
                cols_expr = ", ".join(f"{q_fn(dst_table)}.{q_fn(c)}" for c in related_cols)
                placeholders = ", ".join(["%s"] * len(pk_values))
                sql = (
                    f'SELECT {cols_expr}, {q_fn(junction)}.{q_fn(src_col)} AS _prefetch_src_id'
                    f' FROM {q_fn(dst_table)}'
                    f' JOIN {q_fn(junction)} ON {q_fn(junction)}.{q_fn(dst_col)} = {q_fn(dst_table)}.{q_fn(related_pk)}'
                    f' WHERE {q_fn(junction)}.{q_fn(src_col)} IN ({placeholders})'
                )
                async with _use_async_conn(cfg) as conn:
                    rows = await conn.execute(sql, pk_values, as_dict=True)

                grouped: Dict[Any, List] = {}
                for row in rows:
                    row = dict(row)
                    src_id = row.pop("_prefetch_src_id")
                    grouped.setdefault(src_id, []).append(related_model.from_row(row))

                pk_col2 = self._model._get_pk_column()
                for inst in instances:
                    src_id = getattr(inst, pk_col2, None)
                    object.__setattr__(inst, f"_prefetched_{attr}", grouped.get(src_id, []))

    # ── sync execution ──────────────────────────────────────────────────────

    def all(self) -> List[Any]:
        """Execute and return a list of model instances (or dicts/tuples if values/values_list)."""
        cfg = self._cfg_read()
        with _use_sync_conn(cfg) as conn:
            backend = conn.backend
            sql, params = self._build_select_sql(backend)
            rows = conn.execute(sql, params, as_dict=True)
        return self._convert_rows([dict(r) for r in rows])

    def _convert_rows(self, rows: List[Dict]) -> List[Any]:
        """Convert raw rows to the requested format: instances, dicts, or tuples."""
        if self._values_fields is not None:
            return rows  # already dicts

        if self._values_list_fields is not None:
            if self._flat:
                field = self._values_list_fields[0]
                return [r[field] for r in rows]
            return [tuple(r[f] for f in self._values_list_fields) for r in rows]

        if self._annotations and self._values_fields is None and self._values_list_fields is None:
            # Annotations on instances — attach annotation values as attributes
            instances = self._rows_to_instances(rows)
            for inst, row in zip(instances, rows):
                for alias in self._annotations:
                    object.__setattr__(inst, alias, row.get(alias))
            return instances

        return self._rows_to_instances(rows)

    def first(self) -> Optional[Any]:
        results = self.limit(1).all()
        return results[0] if results else None

    def get(self, **kwargs) -> Any:
        qs = self.filter(**kwargs) if kwargs else self
        results = qs.limit(2).all()
        if not results:
            raise self._model.DoesNotExist(
                f"{self._model.__name__} matching query does not exist."
            )
        if len(results) > 1:
            raise self._model.MultipleObjectsReturned(
                f"get() returned more than one {self._model.__name__}."
            )
        return results[0]

    def count(self) -> int:
        from ..sql.builder import build_select
        cfg = self._cfg_read()
        with _use_sync_conn(cfg) as conn:
            backend = conn.backend
            where_sql, where_params = self._build_where(backend)
            sql, params = build_select(
                backend,
                self._model._get_table(),
                [],
                where_sql=where_sql or None,
                where_params=where_params or None,
                extra_selects=[("COUNT(*)", "n")],
            )
            rows = conn.execute(sql, params, as_dict=True)
        return rows[0]["n"] if rows else 0

    def exists(self) -> bool:
        return self.limit(1).count() > 0

    def create(self, **kwargs) -> Any:
        import datetime
        from ..sql.builder import build_insert
        cfg = self._cfg_write()
        now = datetime.datetime.now()
        for col in getattr(self._model, "_auto_now_cols", []):
            kwargs.setdefault(col, now)
        for col in getattr(self._model, "_auto_now_add_cols", []):
            kwargs.setdefault(col, now)
        with _use_sync_conn(cfg) as conn:
            backend = conn.backend
            table = self._model._get_table()
            pk_col = self._model._get_pk_column()
            cols = list(kwargs.keys())
            vals = list(kwargs.values())
            returning = None if pk_col in kwargs else pk_col
            sql, params = build_insert(backend, table, cols, vals, returning=returning)
            rows = conn.execute(sql, params, as_dict=True)
            if returning and rows:
                kwargs[pk_col] = rows[0][returning]
        return self._model.from_row(kwargs)

    def bulk_create(self, objects: List[Dict]) -> List[Any]:
        """
        Insert multiple rows in a single query.

            Item.objects.bulk_create([
                {"name": "A", "price": 10.0, "in_stock": True},
                {"name": "B", "price": 20.0, "in_stock": False},
            ])
        """
        if not objects:
            return []
        from ..sql.builder import build_bulk_insert
        cfg = self._cfg_write()
        pk_col = self._model._get_pk_column()
        columns = list(objects[0].keys())
        rows_vals = [list(obj.values()) for obj in objects]
        returning = pk_col if pk_col not in columns else None
        with _use_sync_conn(cfg) as conn:
            backend = conn.backend
            sql, params = build_bulk_insert(
                backend, self._model._get_table(), columns, rows_vals, returning=returning
            )
            result_rows = conn.execute(sql, params, as_dict=True)
        instances = []
        for i, obj in enumerate(objects):
            row = dict(obj)
            if returning and i < len(result_rows):
                row[pk_col] = result_rows[i][pk_col]
            instances.append(self._model.from_row(row))
        return instances

    def bulk_update(self, objects: List[Any], fields: List[str]) -> None:
        """
        Update specific fields on multiple model instances using individual UPDATEs
        wrapped in a single transaction.

            items[0].price = 99.0
            items[1].price = 49.0
            Item.objects.bulk_update(items, fields=["price"])
        """
        if not objects:
            return
        pk_col = self._model._get_pk_column()
        cfg = self._cfg_write()
        q_fn = None
        with _use_sync_conn(cfg) as conn:
            backend = conn.backend
            q_fn = backend.quote_ident
            with conn.atomic():
                for obj in objects:
                    pk_val = getattr(obj, pk_col)
                    set_parts = [f"{q_fn(f)} = %s" for f in fields]
                    vals = [getattr(obj, f) for f in fields] + [pk_val]
                    sql = (
                        f"UPDATE {q_fn(self._model._get_table())}"
                        f" SET {', '.join(set_parts)}"
                        f" WHERE {q_fn(pk_col)} = %s"
                    )
                    conn.execute(sql, vals, as_dict=False)

    def get_or_create(self, defaults: Optional[Dict] = None, **kwargs) -> Tuple[Any, bool]:
        """
        Look up an object by `kwargs`, creating one with `defaults` if not found.
        Returns (instance, created) where created is True if it was inserted.

            item, created = Item.objects.get_or_create(
                name="Widget",
                defaults={"price": 9.99, "in_stock": True}
            )
        """
        try:
            obj = self.get(**kwargs)
            return obj, False
        except self._model.DoesNotExist:
            create_kwargs = {**kwargs, **(defaults or {})}
            obj = self.create(**create_kwargs)
            return obj, True

    def update_or_create(self, defaults: Optional[Dict] = None, **kwargs) -> Tuple[Any, bool]:
        """
        Update an existing object (by `kwargs`) with `defaults`, or create it.
        Returns (instance, created).

            item, created = Item.objects.update_or_create(
                name="Widget",
                defaults={"price": 9.99, "in_stock": True}
            )
        """
        try:
            obj = self.get(**kwargs)
            for field, value in (defaults or {}).items():
                object.__setattr__(obj, field, value)
            pk_col = self._model._get_pk_column()
            pk_val = getattr(obj, pk_col)
            self.filter(**{pk_col: pk_val}).update(**(defaults or {}))
            return obj, False
        except self._model.DoesNotExist:
            create_kwargs = {**kwargs, **(defaults or {})}
            obj = self.create(**create_kwargs)
            return obj, True

    def update(self, **kwargs) -> int:
        from .f import F
        if not self._where_nodes:
            raise ValueError("Refusing to UPDATE with no filters. Use filter() first.")
        cfg = self._cfg_write()
        with _use_sync_conn(cfg) as conn:
            backend = conn.backend
            table = self._model._get_table()
            where_sql, where_params = self._build_where(backend)
            q = backend.quote_ident
            set_parts, set_params = [], []
            for col, val in kwargs.items():
                if isinstance(val, F):
                    set_parts.append(f"{q(col)} = {q(val.field)}")
                else:
                    set_parts.append(f"{q(col)} = %s")
                    set_params.append(val)
            params = set_params + where_params
            sql = (
                f"UPDATE {q(table)} SET {', '.join(set_parts)}"
                f" WHERE {where_sql}"
            )
            conn.execute(sql, params, as_dict=True)
        return -1  # rowcount not easily exposed; return -1 as sentinel

    def delete(self) -> int:
        if not self._where_nodes:
            raise ValueError("Refusing to DELETE with no filters. Use filter() first.")
        cfg = self._cfg_write()
        with _use_sync_conn(cfg) as conn:
            backend = conn.backend
            table = self._model._get_table()
            q = backend.quote_ident
            where_sql, where_params = self._build_where(backend)
            sql = f"DELETE FROM {q(table)} WHERE {where_sql}"
            conn.execute(sql, where_params, as_dict=True)
        return -1

    def aggregate(self, **kwargs) -> Dict[str, Any]:
        """
        Execute immediately. Returns a dict of computed values.

            Item.objects.aggregate(total=Sum("price"), count=Count("id"))
            # → {"total": 450.0, "count": 9}
        """
        from .aggregates import Aggregate
        from ..sql.builder import build_select

        cfg = self._cfg_read()
        with _use_sync_conn(cfg) as conn:
            backend = conn.backend
            extra_selects = []
            for alias, expr in kwargs.items():
                if isinstance(expr, Aggregate):
                    extra_selects.append((expr.as_sql(backend), alias))
                else:
                    extra_selects.append((str(expr), alias))

            where_sql, where_params = self._build_where(backend)
            sql, params = build_select(
                backend,
                self._model._get_table(),
                [],
                where_sql=where_sql or None,
                where_params=where_params or None,
                extra_selects=extra_selects,
            )
            rows = conn.execute(sql, params, as_dict=True)

        return dict(rows[0]) if rows else {alias: None for alias in kwargs}

    def raw(self, sql: str, params: Optional[List] = None) -> List[Any]:
        """
        Execute raw SQL and return model instances.

            User.objects.raw("SELECT * FROM users WHERE email LIKE %s", ["%@example.com"])
        """
        cfg = self._cfg_read()
        with _use_sync_conn(cfg) as conn:
            rows = conn.execute(sql, params or [], as_dict=True)
        return [self._model.from_row(dict(r)) for r in rows]

    # ── async execution ─────────────────────────────────────────────────────

    async def aall(self) -> List[Any]:
        return await self.alist()

    async def alist(self) -> List[Any]:
        cfg = self._cfg_read()
        async with _use_async_conn(cfg) as conn:
            backend = conn.backend
            sql, params = self._build_select_sql(backend)
            rows = await conn.execute(sql, params, as_dict=True)
        instances = self._convert_rows([dict(r) for r in rows])
        await self._apply_prefetch_async(instances)
        return instances

    async def afirst(self) -> Optional[Any]:
        results = await self.limit(1).alist()
        return results[0] if results else None

    async def aget(self, **kwargs) -> Any:
        qs = self.filter(**kwargs) if kwargs else self
        results = await qs.limit(2).alist()
        if not results:
            raise self._model.DoesNotExist(
                f"{self._model.__name__} matching query does not exist."
            )
        if len(results) > 1:
            raise self._model.MultipleObjectsReturned(
                f"get() returned more than one {self._model.__name__}."
            )
        return results[0]

    async def acreate(self, **kwargs) -> Any:
        import datetime
        from ..sql.builder import build_insert
        cfg = self._cfg_write()
        now = datetime.datetime.now()
        for col in getattr(self._model, "_auto_now_cols", []):
            kwargs.setdefault(col, now)
        for col in getattr(self._model, "_auto_now_add_cols", []):
            kwargs.setdefault(col, now)
        async with _use_async_conn(cfg) as conn:
            backend = conn.backend
            table = self._model._get_table()
            pk_col = self._model._get_pk_column()
            cols = list(kwargs.keys())
            vals = list(kwargs.values())
            returning = None if pk_col in kwargs else pk_col
            sql, params = build_insert(backend, table, cols, vals, returning=returning)
            rows = await conn.execute(sql, params, as_dict=True)
            if returning and rows:
                kwargs[pk_col] = rows[0][returning]
        return self._model.from_row(kwargs)

    async def abulk_create(self, objects: List[Dict]) -> List[Any]:
        """Async version of bulk_create."""
        if not objects:
            return []
        from ..sql.builder import build_bulk_insert
        cfg = self._cfg_write()
        pk_col = self._model._get_pk_column()
        columns = list(objects[0].keys())
        rows_vals = [list(obj.values()) for obj in objects]
        returning = pk_col if pk_col not in columns else None
        async with _use_async_conn(cfg) as conn:
            backend = conn.backend
            sql, params = build_bulk_insert(
                backend, self._model._get_table(), columns, rows_vals, returning=returning
            )
            result_rows = await conn.execute(sql, params, as_dict=True)
        instances = []
        for i, obj in enumerate(objects):
            row = dict(obj)
            if returning and i < len(result_rows):
                row[pk_col] = result_rows[i][pk_col]
            instances.append(self._model.from_row(row))
        return instances

    async def abulk_update(self, objects: List[Any], fields: List[str]) -> None:
        """Async version of bulk_update."""
        if not objects:
            return
        pk_col = self._model._get_pk_column()
        cfg = self._cfg_write()
        async with _use_async_conn(cfg) as conn:
            backend = conn.backend
            q_fn = backend.quote_ident
            async with conn.atomic():
                for obj in objects:
                    pk_val = getattr(obj, pk_col)
                    set_parts = [f"{q_fn(f)} = %s" for f in fields]
                    vals = [getattr(obj, f) for f in fields] + [pk_val]
                    sql = (
                        f"UPDATE {q_fn(self._model._get_table())}"
                        f" SET {', '.join(set_parts)}"
                        f" WHERE {q_fn(pk_col)} = %s"
                    )
                    await conn.execute(sql, vals, as_dict=False)

    async def aget_or_create(self, defaults: Optional[Dict] = None, **kwargs) -> Tuple[Any, bool]:
        """Async version of get_or_create."""
        try:
            obj = await self.aget(**kwargs)
            return obj, False
        except self._model.DoesNotExist:
            create_kwargs = {**kwargs, **(defaults or {})}
            obj = await self.acreate(**create_kwargs)
            return obj, True

    async def aupdate_or_create(self, defaults: Optional[Dict] = None, **kwargs) -> Tuple[Any, bool]:
        """Async version of update_or_create."""
        try:
            obj = await self.aget(**kwargs)
            for field, value in (defaults or {}).items():
                object.__setattr__(obj, field, value)
            pk_col = self._model._get_pk_column()
            pk_val = getattr(obj, pk_col)
            await self.filter(**{pk_col: pk_val}).aupdate(**(defaults or {}))
            return obj, False
        except self._model.DoesNotExist:
            create_kwargs = {**kwargs, **(defaults or {})}
            obj = await self.acreate(**create_kwargs)
            return obj, True

    async def acount(self) -> int:
        from ..sql.builder import build_select
        cfg = self._cfg_read()
        async with _use_async_conn(cfg) as conn:
            backend = conn.backend
            where_sql, where_params = self._build_where(backend)
            sql, params = build_select(
                backend,
                self._model._get_table(),
                [],
                where_sql=where_sql or None,
                where_params=where_params or None,
                extra_selects=[("COUNT(*)", "n")],
            )
            rows = await conn.execute(sql, params, as_dict=True)
        return rows[0]["n"] if rows else 0

    async def aexists(self) -> bool:
        return await self.limit(1).acount() > 0

    async def aupdate(self, **kwargs) -> None:
        from .f import F
        if not self._where_nodes:
            raise ValueError("Refusing to UPDATE with no filters. Use filter() first.")
        cfg = self._cfg_write()
        async with _use_async_conn(cfg) as conn:
            backend = conn.backend
            table = self._model._get_table()
            where_sql, where_params = self._build_where(backend)
            q = backend.quote_ident
            set_parts, set_params = [], []
            for col, val in kwargs.items():
                if isinstance(val, F):
                    set_parts.append(f"{q(col)} = {q(val.field)}")
                else:
                    set_parts.append(f"{q(col)} = %s")
                    set_params.append(val)
            params = set_params + where_params
            sql = (
                f"UPDATE {q(table)} SET {', '.join(set_parts)}"
                f" WHERE {where_sql}"
            )
            await conn.execute(sql, params, as_dict=True)

    async def adelete(self) -> None:
        if not self._where_nodes:
            raise ValueError("Refusing to DELETE with no filters. Use filter() first.")
        cfg = self._cfg_write()
        async with _use_async_conn(cfg) as conn:
            backend = conn.backend
            table = self._model._get_table()
            q = backend.quote_ident
            where_sql, where_params = self._build_where(backend)
            sql = f"DELETE FROM {q(table)} WHERE {where_sql}"
            await conn.execute(sql, where_params, as_dict=True)

    async def aaggregate(self, **kwargs) -> Dict[str, Any]:
        from .aggregates import Aggregate
        from ..sql.builder import build_select
        cfg = self._cfg_read()
        async with _use_async_conn(cfg) as conn:
            backend = conn.backend
            extra_selects = []
            for alias, expr in kwargs.items():
                if isinstance(expr, Aggregate):
                    extra_selects.append((expr.as_sql(backend), alias))
                else:
                    extra_selects.append((str(expr), alias))
            where_sql, where_params = self._build_where(backend)
            sql, params = build_select(
                backend,
                self._model._get_table(),
                [],
                where_sql=where_sql or None,
                where_params=where_params or None,
                extra_selects=extra_selects,
            )
            rows = await conn.execute(sql, params, as_dict=True)
        return dict(rows[0]) if rows else {alias: None for alias in kwargs}

    async def araw(self, sql: str, params: Optional[List] = None) -> List[Any]:
        cfg = self._cfg_read()
        async with _use_async_conn(cfg) as conn:
            rows = await conn.execute(sql, params or [], as_dict=True)
        return [self._model.from_row(dict(r)) for r in rows]

    # ── Python protocol ──────────────────────────────────────────────────────

    def __iter__(self):
        return iter(self.all())

    def __repr__(self) -> str:
        return f"<QuerySet model={self._model.__name__} where={self._where_nodes}>"


# ── Manager ───────────────────────────────────────────────────────────────────

class Manager:
    """Attached to every Model as `Model.objects`. Entry point for all queries."""

    def __init__(self, model_class: Any) -> None:
        self._model = model_class

    def _qs(self) -> QuerySet:
        return QuerySet(self._model)

    def using(self, alias: str) -> QuerySet:
        """
        Return a QuerySet that targets the given database alias::

            Report.objects.using("analytics").filter(published=True).all()
        """
        return self._qs().using(alias)

    # ── sync ────────────────────────────────────────────────────────────────

    def all(self) -> List[Any]:
        return self._qs().all()

    def filter(self, *q_objects, **kwargs) -> QuerySet:
        return self._qs().filter(*q_objects, **kwargs)

    def exclude(self, *q_objects, **kwargs) -> QuerySet:
        return self._qs().exclude(*q_objects, **kwargs)

    def get(self, **kwargs) -> Any:
        return self._qs().get(**kwargs)

    def create(self, **kwargs) -> Any:
        return self._qs().create(**kwargs)

    def bulk_create(self, objects: List[Dict]) -> List[Any]:
        return self._qs().bulk_create(objects)

    def bulk_update(self, objects: List[Any], fields: List[str]) -> None:
        return self._qs().bulk_update(objects, fields)

    def get_or_create(self, defaults: Optional[Dict] = None, **kwargs) -> Tuple[Any, bool]:
        return self._qs().get_or_create(defaults=defaults, **kwargs)

    def update_or_create(self, defaults: Optional[Dict] = None, **kwargs) -> Tuple[Any, bool]:
        return self._qs().update_or_create(defaults=defaults, **kwargs)

    def select_for_update(self) -> QuerySet:
        return self._qs().select_for_update()

    def having(self, *q_objects, **kwargs) -> QuerySet:
        return self._qs().having(*q_objects, **kwargs)

    def first(self) -> Optional[Any]:
        return self._qs().first()

    def order_by(self, *fields: str) -> QuerySet:
        return self._qs().order_by(*fields)

    def count(self) -> int:
        return self._qs().count()

    def exists(self) -> bool:
        return self._qs().exists()

    def aggregate(self, **kwargs) -> Dict[str, Any]:
        return self._qs().aggregate(**kwargs)

    def annotate(self, **kwargs) -> QuerySet:
        return self._qs().annotate(**kwargs)

    def values(self, *fields: str) -> QuerySet:
        return self._qs().values(*fields)

    def values_list(self, *fields: str, flat: bool = False) -> QuerySet:
        return self._qs().values_list(*fields, flat=flat)

    def distinct(self) -> QuerySet:
        return self._qs().distinct()

    def select_related(self, *fields: str) -> QuerySet:
        return self._qs().select_related(*fields)

    def prefetch_related(self, *fields: str) -> QuerySet:
        return self._qs().prefetch_related(*fields)

    def raw(self, sql: str, params: Optional[List] = None) -> List[Any]:
        return self._qs().raw(sql, params)

    def only(self, *fields: str) -> QuerySet:
        return self._qs().only(*fields)

    def defer(self, *fields: str) -> QuerySet:
        return self._qs().defer(*fields)

    def delete(self) -> None:
        raise ValueError("Call filter() before delete() on the manager.")

    # ── async ────────────────────────────────────────────────────────────────

    async def aall(self) -> List[Any]:
        return await self._qs().alist()

    async def alist(self) -> List[Any]:
        return await self._qs().alist()

    async def aget(self, **kwargs) -> Any:
        return await self._qs().aget(**kwargs)

    async def acreate(self, **kwargs) -> Any:
        return await self._qs().acreate(**kwargs)

    async def abulk_create(self, objects: List[Dict]) -> List[Any]:
        return await self._qs().abulk_create(objects)

    async def abulk_update(self, objects: List[Any], fields: List[str]) -> None:
        return await self._qs().abulk_update(objects, fields)

    async def aget_or_create(self, defaults: Optional[Dict] = None, **kwargs) -> Tuple[Any, bool]:
        return await self._qs().aget_or_create(defaults=defaults, **kwargs)

    async def aupdate_or_create(self, defaults: Optional[Dict] = None, **kwargs) -> Tuple[Any, bool]:
        return await self._qs().aupdate_or_create(defaults=defaults, **kwargs)

    async def afirst(self) -> Optional[Any]:
        return await self._qs().afirst()

    async def acount(self) -> int:
        return await self._qs().acount()

    async def aexists(self) -> bool:
        return await self._qs().aexists()

    async def aaggregate(self, **kwargs) -> Dict[str, Any]:
        return await self._qs().aaggregate(**kwargs)

    async def araw(self, sql: str, params: Optional[List] = None) -> List[Any]:
        return await self._qs().araw(sql, params)

    def __repr__(self) -> str:
        return f"<Manager model={self._model.__name__}>"
