"""
Legacy QuerySet and AsyncQuerySet — connection-based, kept for RelatedAccessor compatibility.
NotFound and MultipleObjects exceptions.
"""
from typing import Any, List, Optional, Type, TypeVar

from .model import Model, column_names, pk_column, table_name
from ..sql import build_insert, build_select

M = TypeVar("M", bound=Model)


class QuerySet:
    """Sync QuerySet (connection-based). Used by RelatedAccessor."""

    def __init__(
        self,
        model: Type[M],
        connection: Any,
        _filter_pk: Optional[Any] = None,
        _filter_limit: Optional[int] = None,
    ) -> None:
        self._model = model
        self._conn = connection
        self._filter_pk = _filter_pk
        self._filter_limit = _filter_limit

    def filter(self, *, pk: Optional[Any] = None, limit: Optional[int] = None) -> "QuerySet":
        return QuerySet(
            self._model, self._conn,
            _filter_pk=pk if pk is not None else self._filter_pk,
            _filter_limit=limit if limit is not None else self._filter_limit,
        )

    def all(self, limit: Optional[int] = None) -> List[M]:
        backend = self._conn.backend
        table = table_name(self._model)
        columns = column_names(self._model)
        where = None
        if self._filter_pk is not None:
            where = {pk_column(self._model): self._filter_pk}
        lim = limit if limit is not None else self._filter_limit
        sql, params = build_select(backend, table, columns, where=where, limit=lim)
        rows = self._conn.execute(sql, params, as_dict=True)
        return [self._model.from_row(dict(r)) for r in rows]

    def get(self, *, pk: Any) -> M:
        backend = self._conn.backend
        table = table_name(self._model)
        columns = column_names(self._model)
        where = {pk_column(self._model): pk}
        sql, params = build_select(backend, table, columns, where=where, limit=2)
        rows = self._conn.execute(sql, params, as_dict=True)
        if not rows:
            raise NotFound(f"{self._model.__name__} with pk={pk} not found")
        if len(rows) > 1:
            raise MultipleObjects(f"Multiple rows for pk={pk}")
        return self._model.from_row(dict(rows[0]))

    def create(self, **kwargs: Any) -> M:
        backend = self._conn.backend
        table = table_name(self._model)
        pk_col = pk_column(self._model)
        cols = list(kwargs.keys())
        vals = list(kwargs.values())
        returning = None if pk_col in kwargs else pk_col
        sql, params = build_insert(backend, table, cols, vals, returning=returning)
        rows = self._conn.execute(sql, params, as_dict=True)
        if returning and rows:
            kwargs = dict(kwargs)
            kwargs[pk_col] = rows[0][returning]
        return self._model.from_row(kwargs)


class AsyncQuerySet:
    """Async QuerySet (connection-based). Used by RelatedAccessor."""

    def __init__(
        self,
        model: Type[M],
        connection: Any,
        _filter_pk: Optional[Any] = None,
        _filter_limit: Optional[int] = None,
    ) -> None:
        self._model = model
        self._conn = connection
        self._filter_pk = _filter_pk
        self._filter_limit = _filter_limit

    def filter(self, *, pk: Optional[Any] = None, limit: Optional[int] = None) -> "AsyncQuerySet":
        return AsyncQuerySet(
            self._model, self._conn,
            _filter_pk=pk if pk is not None else self._filter_pk,
            _filter_limit=limit if limit is not None else self._filter_limit,
        )

    async def alist(self, limit: Optional[int] = None) -> List[M]:
        backend = self._conn.backend
        table = table_name(self._model)
        columns = column_names(self._model)
        where = None
        if self._filter_pk is not None:
            where = {pk_column(self._model): self._filter_pk}
        lim = limit if limit is not None else self._filter_limit
        sql, params = build_select(backend, table, columns, where=where, limit=lim)
        rows = await self._conn.execute(sql, params, as_dict=True)
        return [self._model.from_row(dict(r)) for r in rows]

    async def aget(self, *, pk: Any) -> M:
        backend = self._conn.backend
        table = table_name(self._model)
        columns = column_names(self._model)
        where = {pk_column(self._model): pk}
        sql, params = build_select(backend, table, columns, where=where, limit=2)
        rows = await self._conn.execute(sql, params, as_dict=True)
        if not rows:
            raise NotFound(f"{self._model.__name__} with pk={pk} not found")
        if len(rows) > 1:
            raise MultipleObjects(f"Multiple rows for pk={pk}")
        return self._model.from_row(dict(rows[0]))

    async def acreate(self, **kwargs: Any) -> M:
        backend = self._conn.backend
        table = table_name(self._model)
        pk_col = pk_column(self._model)
        cols = list(kwargs.keys())
        vals = list(kwargs.values())
        returning = None if pk_col in kwargs else pk_col
        sql, params = build_insert(backend, table, cols, vals, returning=returning)
        rows = await self._conn.execute(sql, params, as_dict=True)
        if returning and rows:
            kwargs = dict(kwargs)
            kwargs[pk_col] = rows[0][returning]
        return self._model.from_row(kwargs)


class NotFound(Exception):
    pass


class MultipleObjects(Exception):
    pass
