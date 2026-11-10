"""
Relation accessors returned when accessing a relation attribute on a Model instance.
  instance.author        → RelatedAccessor        → .get(conn), .aget(conn)
  instance.tags          → ManyToManyAccessor     → .all(conn), .add(conn, obj), .remove(conn, obj)
  author.blog_set        → ReverseFKDescriptor    → returns a pre-filtered QuerySet
"""
from typing import Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .model import Model


# ── Reverse FK descriptor ─────────────────────────────────────────────────────

class ReverseFKDescriptor:
    """
    Descriptor placed on the *related* model to give Django-style reverse access.

    When ``Blog.author = ForeignKey(Author, related_name='blogs')`` is declared,
    ModelMeta attaches ``Author.blogs = ReverseFKDescriptor(Blog, 'author_id')``.

    Accessing ``author_instance.blogs`` returns a QuerySet pre-filtered by the
    FK column, so the full QuerySet API (.filter, .alist, .count, etc.) is
    immediately available::

        blogs = await author.blogs.alist()
        count = await author.blogs.acount()
        published = await author.blogs.filter(published=True).alist()
    """

    def __init__(self, from_model: Any, fk_column: str) -> None:
        self.from_model = from_model   # the model that owns the FK (e.g. Blog)
        self.fk_column  = fk_column    # the FK column on that model (e.g. "author_id")

    def __set_name__(self, owner: Any, name: str) -> None:
        self._name = name

    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        if obj is None:
            return self
        pk_val = obj.__dict__.get(obj.__class__._get_pk_column())
        # Return a QuerySet already filtered by this FK
        return self.from_model.objects.filter(**{self.fk_column: pk_val})

    def __repr__(self) -> str:
        return (
            f"<ReverseFKDescriptor from={self.from_model.__name__} "
            f"fk={self.fk_column}>"
        )


class RelatedAccessor:
    """Accessor for ForeignKey / OneToOneField (fallback when no global config)."""

    def __init__(self, instance: "Model", to_model: Any, fk_value: Any) -> None:
        self._instance = instance
        self._to_model = to_model
        self._fk_value = fk_value

    def __repr__(self) -> str:
        return f"<RelatedAccessor to={self._to_model.__name__} fk={self._fk_value}>"

    def get(self, connection: Any) -> "Model":
        from .queryset import QuerySet, NotFound
        if self._fk_value is None:
            raise NotFound(f"FK value is None; cannot fetch {self._to_model.__name__}")
        qs = QuerySet(self._to_model, connection)
        return qs.get(pk=self._fk_value)

    async def aget(self, connection: Any) -> "Model":
        from .queryset import AsyncQuerySet, NotFound
        if self._fk_value is None:
            raise NotFound(f"FK value is None; cannot fetch {self._to_model.__name__}")
        qs = AsyncQuerySet(self._to_model, connection)
        return await qs.aget(pk=self._fk_value)


class ManyToManyAccessor:
    """Accessor for ManyToManyField."""

    def __init__(
        self,
        instance: "Model",
        to_model: Any,
        junction_table: str,
        src_col: str,
        dst_col: str,
    ) -> None:
        self._instance = instance
        self._to_model = to_model
        self._junction = junction_table
        self._src_col = src_col
        self._dst_col = dst_col

    def __repr__(self) -> str:
        return (
            f"<ManyToManyAccessor to={self._to_model.__name__} "
            f"junction={self._junction}>"
        )

    def _src_pk(self) -> Any:
        return getattr(self._instance, self._instance._get_pk_column(), None)

    def all(self, connection: Any) -> List["Model"]:
        from .queryset import QuerySet
        from ..sql import build_select
        backend = connection.backend
        src_pk = self._src_pk()
        sql, params = build_select(
            backend, self._junction, [self._dst_col],
            where={self._src_col: src_pk},
        )
        rows = connection.execute(sql, params, as_dict=True)
        dst_ids = [r[self._dst_col] for r in rows]
        if not dst_ids:
            return []
        qs = QuerySet(self._to_model, connection)
        return [qs.get(pk=pk_val) for pk_val in dst_ids]

    def add(self, connection: Any, obj: "Model") -> None:
        from ..sql import build_insert
        backend = connection.backend
        src_pk = self._src_pk()
        dst_pk = getattr(obj, obj._get_pk_column())
        sql, params = build_insert(
            backend, self._junction,
            [self._src_col, self._dst_col],
            [src_pk, dst_pk],
        )
        sql += " ON CONFLICT DO NOTHING"
        connection.execute(sql, params, as_dict=True)

    def remove(self, connection: Any, obj: "Model") -> None:
        backend = connection.backend
        src_pk = self._src_pk()
        dst_pk = getattr(obj, obj._get_pk_column())
        q_junc = backend.quote_ident(self._junction)
        q_src = backend.quote_ident(self._src_col)
        q_dst = backend.quote_ident(self._dst_col)
        sql = f"DELETE FROM {q_junc} WHERE {q_src} = %s AND {q_dst} = %s"
        connection.execute(sql, [src_pk, dst_pk], as_dict=True)

    async def aall(self, connection: Any) -> List["Model"]:
        from .queryset import AsyncQuerySet
        from ..sql import build_select
        backend = connection.backend
        src_pk = self._src_pk()
        sql, params = build_select(
            backend, self._junction, [self._dst_col],
            where={self._src_col: src_pk},
        )
        rows = await connection.execute(sql, params, as_dict=True)
        dst_ids = [r[self._dst_col] for r in rows]
        if not dst_ids:
            return []
        qs = AsyncQuerySet(self._to_model, connection)
        return [await qs.aget(pk=pk_val) for pk_val in dst_ids]

    async def aadd(self, connection: Any, obj: "Model") -> None:
        from ..sql import build_insert
        backend = connection.backend
        src_pk = self._src_pk()
        dst_pk = getattr(obj, obj._get_pk_column())
        sql, params = build_insert(
            backend, self._junction,
            [self._src_col, self._dst_col],
            [src_pk, dst_pk],
        )
        sql += " ON CONFLICT DO NOTHING"
        await connection.execute(sql, params, as_dict=True)

    async def aremove(self, connection: Any, obj: "Model") -> None:
        backend = connection.backend
        src_pk = self._src_pk()
        dst_pk = getattr(obj, obj._get_pk_column())
        q_junc = backend.quote_ident(self._junction)
        q_src = backend.quote_ident(self._src_col)
        q_dst = backend.quote_ident(self._dst_col)
        sql = f"DELETE FROM {q_junc} WHERE {q_src} = %s AND {q_dst} = %s"
        await connection.execute(sql, [src_pk, dst_pk], as_dict=True)
