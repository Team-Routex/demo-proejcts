"""
Backend-agnostic SQL builders.

All functions take `backend` as the first argument so identifier quoting
and placeholder styles are delegated to the backend.
Placeholders are always %s here; the asyncpg backend converts them to $1,$2,…
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple


def build_select(
    backend: Any,
    table: str,
    columns: Sequence[str],
    *,
    where: Optional[Dict[str, Any]] = None,
    where_sql: Optional[str] = None,
    where_params: Optional[List[Any]] = None,
    extra_select_params: Optional[List[Any]] = None,
    joins: Optional[List[str]] = None,
    extra_selects: Optional[List[Tuple[str, str]]] = None,
    group_by: Optional[List[str]] = None,
    having_sql: Optional[str] = None,
    having_params: Optional[List[Any]] = None,
    order_by: Optional[List[str]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    distinct: bool = False,
    for_update: bool = False,
) -> Tuple[str, List[Any]]:
    """
    SELECT [DISTINCT] columns [, extra_selects] FROM table
    [JOIN ...]
    [WHERE ...]
    [GROUP BY ...]
    [HAVING ...]
    [ORDER BY ...]
    [LIMIT n] [OFFSET n]
    [FOR UPDATE]

    Parameters
    ----------
    where           : legacy {col: val} equality dict (backward compat, e.g. used by FK auto-fetch)
    where_sql       : pre-built WHERE fragment (without the word WHERE)
    where_params    : params that go with where_sql
    joins           : list of raw JOIN clauses, e.g. ["LEFT JOIN users ON users.id = posts.author_id"]
    extra_selects   : list of (expression, alias) added to SELECT, e.g. [("COUNT(*)", "n")]
    group_by        : list of column names to GROUP BY
    having_sql      : pre-built HAVING fragment (without the word HAVING)
    having_params   : params for having_sql
    order_by        : list of column names; prefix with "-" for DESC
    distinct        : add DISTINCT after SELECT
    for_update      : append FOR UPDATE (row locking)
    """
    q = backend.quote_ident
    params: List[Any] = []

    # ---- SELECT ----
    # Params are ordered by their position in the generated SQL.
    # extra_select_params come from SELECT-level expressions (Subquery, Coalesce+Value, etc.)
    # and must precede WHERE params since SELECT appears before WHERE in SQL.
    select_params: List[Any] = list(extra_select_params or [])

    distinct_kw = "DISTINCT " if distinct else ""
    cols_sql = ", ".join(f"{q(table)}.{q(c)}" for c in columns)

    if extra_selects:
        extra_sql = ", ".join(f"{expr} AS {q(alias)}" for expr, alias in extra_selects)
        cols_sql = f"{cols_sql}, {extra_sql}" if cols_sql else extra_sql

    sql = f"SELECT {distinct_kw}{cols_sql} FROM {q(table)}"

    # ---- JOINs ----
    if joins:
        sql += " " + " ".join(joins)

    # ---- WHERE ----
    # Precedence: where_sql (from QuerySet) > where dict (legacy)
    params: List[Any] = []
    if where_sql:
        sql += f" WHERE {where_sql}"
        params.extend(where_params or [])
    elif where:
        conditions = []
        for col, val in where.items():
            conditions.append(f"{q(col)} = %s")
            params.append(val)
        sql += " WHERE " + " AND ".join(conditions)

    # ---- GROUP BY ----
    if group_by:
        sql += " GROUP BY " + ", ".join(q(c) for c in group_by)

    # ---- HAVING ----
    if having_sql:
        sql += f" HAVING {having_sql}"
        params.extend(having_params or [])

    # ---- ORDER BY ----
    if order_by:
        parts = []
        for col in order_by:
            if col.startswith("-"):
                parts.append(f"{q(col[1:])} DESC")
            else:
                parts.append(f"{q(col)} ASC")
        sql += " ORDER BY " + ", ".join(parts)

    # ---- LIMIT / OFFSET ----
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    if offset is not None:
        sql += f" OFFSET {int(offset)}"

    # ---- FOR UPDATE ----
    if for_update:
        sql += " FOR UPDATE"

    # SELECT-level params (from Subquery / Coalesce+Value) precede WHERE params
    return sql, select_params + params


def build_insert(
    backend: Any,
    table: str,
    columns: Sequence[str],
    values: Sequence[Any],
    returning: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    """INSERT INTO table (cols) VALUES (%s, …) [RETURNING col]"""
    q = backend.quote_ident
    cols_sql = ", ".join(q(c) for c in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO {q(table)} ({cols_sql}) VALUES ({placeholders})"
    if returning and backend.supports_returning():
        sql += f" RETURNING {q(returning)}"
    return sql, list(values)


def build_bulk_insert(
    backend: Any,
    table: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    returning: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    """
    INSERT INTO table (cols) VALUES (%s,…), (%s,…), … [RETURNING col]
    All rows must have the same column order.
    """
    q = backend.quote_ident
    cols_sql = ", ".join(q(c) for c in columns)
    row_placeholder = f"({', '.join(['%s'] * len(columns))})"
    all_placeholders = ", ".join(row_placeholder for _ in rows)
    params: List[Any] = [v for row in rows for v in row]
    sql = f"INSERT INTO {q(table)} ({cols_sql}) VALUES {all_placeholders}"
    if returning and backend.supports_returning():
        sql += f" RETURNING {q(returning)}"
    return sql, params


def build_update(
    backend: Any,
    table: str,
    set_values: Dict[str, Any],
    where: Dict[str, Any],
) -> Tuple[str, List[Any]]:
    """UPDATE table SET col=%s, … WHERE col=%s [AND …]"""
    q = backend.quote_ident
    set_parts = [f"{q(col)} = %s" for col in set_values]
    params: List[Any] = list(set_values.values())
    where_parts = [f"{q(col)} = %s" for col in where]
    params += list(where.values())
    sql = (
        f"UPDATE {q(table)} SET {', '.join(set_parts)}"
        f" WHERE {' AND '.join(where_parts)}"
    )
    return sql, params


def build_delete(
    backend: Any,
    table: str,
    where: Dict[str, Any],
) -> Tuple[str, List[Any]]:
    """DELETE FROM table WHERE col=%s [AND …]"""
    q = backend.quote_ident
    where_parts = [f"{q(col)} = %s" for col in where]
    params: List[Any] = list(where.values())
    sql = f"DELETE FROM {q(table)} WHERE {' AND '.join(where_parts)}"
    return sql, params
