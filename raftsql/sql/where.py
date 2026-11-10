"""
WHERE clause builder.

Supports:
  - Exact equality:                  filter(name="Alice")
  - Lookup expressions:              filter(age__gte=18), filter(name__icontains="ali")
  - IN / NOT IN:                     filter(id__in=[1,2,3])
  - Subquery IN:                     filter(id__in=Subquery(qs))
  - NULL checks:                     filter(deleted_at__isnull=True)
  - BETWEEN:                         filter(price__range=(10, 100))
  - F() column references:           filter(stock__gt=F("reserved"))
  - OuterRef in correlated subquery: filter(author_id=OuterRef("id"))
  - Q() complex conditions:          filter(Q(a=1) | Q(b=2))
  - Negation:                        exclude(...) → ~Q(...)
"""
from typing import Any, List, Optional, Tuple

_LOOKUPS = {
    "exact":       ("=",     None),
    "ne":          ("!=",    None),
    "gt":          (">",     None),
    "gte":         (">=",    None),
    "lt":          ("<",     None),
    "lte":         ("<=",    None),
    "contains":    ("LIKE",  "contains"),
    "icontains":   ("ILIKE", "contains"),
    "startswith":  ("LIKE",  "startswith"),
    "istartswith": ("ILIKE", "startswith"),
    "endswith":    ("LIKE",  "endswith"),
    "iendswith":   ("ILIKE", "endswith"),
    "regex":       ("~",     None),
    "iregex":      ("~*",    None),
    "in":          (None,    "in"),
    "isnull":      (None,    "isnull"),
    "range":       (None,    "range"),
}

_LOOKUP_NAMES = frozenset(_LOOKUPS)


def _parse_lookup(key: str) -> Tuple[str, str]:
    idx = key.rfind("__")
    if idx != -1:
        suffix = key[idx + 2:]
        if suffix in _LOOKUP_NAMES:
            return key[:idx], suffix
    return key, "exact"


def _node_to_sql(
    key: str,
    value: Any,
    backend: Any,
    params: List,
    outer_table: Optional[str] = None,
    table: Optional[str] = None,
) -> str:
    """Convert a single filter key/value pair into a SQL fragment."""
    from ..orm.f import F
    from ..orm.expressions import OuterRef, Subquery

    q = backend.quote_ident
    field, lookup = _parse_lookup(key)
    # Qualify with base table when joins are present to avoid ambiguous column refs
    col = f"{q(table)}.{q(field)}" if table and "." not in field else q(field)
    op, transform = _LOOKUPS[lookup]

    # IS NULL / IS NOT NULL
    if transform == "isnull":
        return f"{col} IS NULL" if value else f"{col} IS NOT NULL"

    # IN (...) — supports both plain lists and Subquery
    if transform == "in":
        if isinstance(value, Subquery):
            resolved = value.resolve(outer_table) if outer_table else value
            sub_sql = resolved.as_sql(backend, params)
            return f"{col} IN {sub_sql}"
        if not value:
            return "1=0"
        placeholders = ", ".join(["%s"] * len(value))
        params.extend(value)
        return f"{col} IN ({placeholders})"

    # BETWEEN %s AND %s
    if transform == "range":
        params.extend([value[0], value[1]])
        return f"{col} BETWEEN %s AND %s"

    # OuterRef — correlated subquery reference to outer query column
    if isinstance(value, OuterRef):
        if outer_table:
            return f"{col} {op} {outer_table}.{q(value.field)}"
        return f"{col} {op} {q(value.field)}"

    # Subquery on right-hand side: col = (SELECT ...)
    if isinstance(value, Subquery):
        resolved = value.resolve(outer_table) if outer_table else value
        sub_sql = resolved.as_sql(backend, params)
        return f"{col} {op} {sub_sql}"

    # F() — column reference on right-hand side
    if isinstance(value, F):
        return f"{col} {op} {q(value.field)}"

    # LIKE / ILIKE value transforms
    if transform == "contains":
        params.append(f"%{value}%")
    elif transform == "startswith":
        params.append(f"{value}%")
    elif transform == "endswith":
        params.append(f"%{value}")
    else:
        params.append(value)

    return f"{col} {op} %s"


def _build_q(
    q_obj: Any,
    backend: Any,
    params: List,
    outer_table: Optional[str] = None,
    table: Optional[str] = None,
) -> str:
    """Recursively convert a Q object tree into a SQL string."""
    from ..orm.q import Q

    parts = []
    for child in q_obj.children:
        if isinstance(child, Q):
            parts.append(f"({_build_q(child, backend, params, outer_table=outer_table, table=table)})")
        else:
            key, value = child
            parts.append(_node_to_sql(key, value, backend, params, outer_table=outer_table, table=table))

    if not parts:
        return "1=1"

    sep = f" {q_obj.connector} "
    sql = sep.join(parts)

    if q_obj.negated:
        sql = f"NOT ({sql})"

    return sql


def build_where(
    nodes: List,
    backend: Any,
    outer_table: Optional[str] = None,
    table: Optional[str] = None,
) -> Tuple[str, List]:
    """
    Build the WHERE clause from a list of Q objects (top-level ANDed).

    Parameters
    ----------
    outer_table : outer query table name, used to qualify OuterRef columns
                  in correlated subqueries.
    table       : base table name; when provided, qualifies all plain column
                  references to avoid ambiguity when JOINs are present.

    Returns
    -------
    (where_sql, params) — where_sql does NOT include the 'WHERE' keyword.
    ("", [])            — if no conditions.
    """
    if not nodes:
        return "", []

    params: List = []
    parts = [_build_q(node, backend, params, outer_table=outer_table, table=table) for node in nodes]
    return " AND ".join(f"({p})" for p in parts), params
