"""
Model base with Django-style Field declarations.
ModelMeta discovers Field/RelationField instances and builds _fields, _field_types,
_pk, _table, _relations, and _m2m metadata automatically.
"""
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar

if TYPE_CHECKING:
    from .options import Options

from . import fields as f
from .fields import Field, AutoField, ForeignKey, ManyToManyField

# ── Global model registry ────────────────────────────────────────────────────
_MODEL_REGISTRY: List[Type["Model"]] = []


def get_registered_models_for_app_label(app_label: str) -> List[Type["Model"]]:
    """Return live model classes with ``_meta.app_label == app_label`` (may be empty)."""
    return [m for m in _MODEL_REGISTRY if getattr(m._meta, "app_label", None) == app_label]


class ProtectedError(Exception):
    """Raised when deleting a model instance that has related rows with on_delete=PROTECT/RESTRICT."""


def _snake(name: str) -> str:
    """ClassName -> class_name."""
    out = []
    for i, c in enumerate(name):
        if c.isupper() and i > 0:
            out.append("_")
        out.append(c.lower())
    return "".join(out)


def _get_column_name(attr_name: str, field: Field) -> str:
    """Return the DB column name for an attribute (e.g. author -> author_id for ForeignKey)."""
    if field.db_column:
        return field.db_column
    if isinstance(field, ForeignKey):  # also covers OneToOneField
        return field.get_column_name(attr_name)
    return attr_name


class ModelMeta(type):
    """
    Metaclass: discovers Field instances declared on the class and builds:
      _table        - table name (Meta.db_table or snake_case class name)
      _fields       - list of DB column names (scalar + FK columns, NOT m2m)
      _field_types  - {column_name: SQL type spec} for migrations
      _pk           - primary key column name
      _relations    - {attr_name: {"column": col, "to": ModelClass, "field": field_obj}}
                      for ForeignKey / OneToOneField
      _m2m          - {attr_name: ManyToManyField} for ManyToManyField
    """

    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        cls = super().__new__(mcs, name, bases, namespace)
        if name == "Model":
            return cls

        # --- Table name ---
        meta = namespace.get("Meta")
        cls._table = (
            getattr(meta, "db_table", None) if meta is not None else None
        ) or _snake(name)

        field_names: List[str] = []
        field_types: Dict[str, str] = {}
        pk_name: Optional[str] = None
        relations: Dict[str, dict] = {}
        m2m: Dict[str, ManyToManyField] = {}
        db_indexes: List[str] = []  # column names where db_index=True

        for attr_name, value in namespace.items():
            if attr_name.startswith("_") or attr_name == "Meta":
                continue
            if not isinstance(value, Field):
                continue

            # Store the attribute name on the field instance so descriptors can use it
            value._attr_name = attr_name

            # ---- ManyToManyField: no column on this table ----
            if isinstance(value, ManyToManyField):
                m2m[attr_name] = value
                continue

            # ---- ForeignKey / OneToOneField: column is attr_id ----
            column_name = _get_column_name(attr_name, value)

            if isinstance(value, ForeignKey):  # covers OneToOneField
                field_names.append(column_name)
                field_types[column_name] = value.get_column_sql()
                relations[attr_name] = {
                    "column": column_name,
                    "to": value.to,
                    "field": value,
                }
            else:
                # ---- Scalar field ----
                field_names.append(column_name)
                if isinstance(value, AutoField):
                    field_types[column_name] = value.get_sql_type()
                elif hasattr(value, "generate_column_sql"):
                    # Fields like PositiveIntegerField need the column name for CHECK
                    field_types[column_name] = value.generate_column_sql(column_name)
                else:
                    field_types[column_name] = value.get_column_sql()
                if value.primary_key:
                    pk_name = column_name

            # Track explicit db_index (non-unique) columns for migration hints
            if getattr(value, 'db_index', False) and not getattr(value, 'unique', False):
                db_indexes.append(column_name)

        cls._fields = field_names
        cls._field_types = field_types
        cls._pk = pk_name or (field_names[0] if field_names else "id")
        cls._relations = relations
        cls._m2m = m2m
        cls._db_indexes = db_indexes  # columns needing a CREATE INDEX

        # ── Multi-table inheritance (MTI) detection ───────────────────────
        # If a base class is itself a concrete Model (not the base "Model" class),
        # this is a child model in an MTI hierarchy.
        mti_parent = None
        for base in bases:
            if (isinstance(base, ModelMeta)
                    and base.__name__ != "Model"
                    and getattr(base, "_fields", None) is not None):
                mti_parent = base
                break

        if mti_parent is not None:
            parent_table = mti_parent._get_table()
            ptr_col = f"{parent_table}_ptr_id"
            cls._parent_model = mti_parent
            cls._ptr_col = ptr_col
            # Ensure ptr column exists in field metadata
            if ptr_col not in field_types:
                field_names.insert(0, ptr_col)
                field_types[ptr_col] = (
                    f'INTEGER NOT NULL REFERENCES "{parent_table}"("id") ON DELETE CASCADE'
                )
                cls._pk = ptr_col
            cls._parent_fields = list(mti_parent._fields)
        else:
            cls._parent_model = None
            cls._ptr_col = None
            cls._parent_fields = []

        # ── Read Meta.constraints ─────────────────────────────────────────
        meta_constraints = []
        if meta is not None:
            for c in getattr(meta, "constraints", []):
                meta_constraints.append(c)
        cls._constraints = meta_constraints

        # ── Django-style _meta (app_label / model_name / db_table / label)
        from .options import Options
        cls._meta = Options(cls, meta)

        # Track auto-timestamp columns for save() / asave()
        auto_now_add_cols: List[str] = []
        auto_now_cols: List[str] = []
        for attr_name, value in namespace.items():
            if isinstance(value, f.DateTimeField):
                col = _get_column_name(attr_name, value)
                if getattr(value, 'auto_now_add', False):
                    auto_now_add_cols.append(col)
                elif getattr(value, 'auto_now', False):
                    auto_now_cols.append(col)
        cls._auto_now_add_cols: List[str] = auto_now_add_cols
        cls._auto_now_cols: List[str] = auto_now_cols

        # Attach Manager as Model.objects
        from .manager import Manager
        cls.objects = Manager(cls)

        # Django-style exceptions scoped to each model
        cls.DoesNotExist = type(f"{name}.DoesNotExist", (Exception,), {})
        cls.MultipleObjectsReturned = type(f"{name}.MultipleObjectsReturned", (Exception,), {})

        # ---- Set up reverse FK accessors on related models ----
        # E.g. Blog.author = ForeignKey(Author, related_name='blogs')
        # → sets Author.blogs = ReverseFKDescriptor(Blog, 'author_id')
        from .relations import ReverseFKDescriptor
        for attr_name, rel in relations.items():
            to_model = rel["to"]
            fk_field = rel["field"]
            fk_col = rel["column"]
            if not isinstance(to_model, type):
                continue  # forward-reference string — skip for now
            reverse_name = getattr(fk_field, "related_name", None) or f"{_snake(name)}_set"
            # Only attach if the related model doesn't already have that attr
            if not hasattr(to_model, reverse_name) or isinstance(
                getattr(to_model, reverse_name, None), ReverseFKDescriptor
            ):
                setattr(to_model, reverse_name, ReverseFKDescriptor(cls, fk_col))

        # Register in global model registry
        _MODEL_REGISTRY.append(cls)

        return cls


class Model(metaclass=ModelMeta):
    """
    Base for all models. Declare fields like Django:

        class Post(Model):
            id      = AutoField(primary_key=True)
            title   = CharField(max_length=200)
            author  = ForeignKey(User, on_delete=CASCADE)
            tags    = ManyToManyField(Tag)

            class Meta:
                db_table = "posts"
    """

    _table: Optional[str] = None
    _pk: str = "id"
    _fields: Optional[List[str]] = None
    _field_types: Optional[Dict[str, str]] = None
    _relations: Dict[str, dict] = {}
    _m2m: Dict[str, "ManyToManyField"] = {}
    _meta: Optional["Options"] = None  # Django-style options; set by metaclass

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    @classmethod
    def _get_table(cls) -> str:
        return cls._table or _snake(cls.__name__)

    @classmethod
    def _get_columns(cls) -> List[str]:
        return list(cls._fields) if cls._fields is not None else [cls._pk]

    @classmethod
    def _get_pk_column(cls) -> str:
        return cls._pk or "id"

    @classmethod
    def from_row(cls: Type["M"], row: Dict[str, Any]) -> "M":
        """Build a model instance from a DB row dict."""
        return cls(**row)

    def save(self) -> None:
        """INSERT (no pk) or UPDATE (has pk). Handles MTI automatically."""
        from ..sql import build_insert, build_update
        from ..db.connection import Connection
        from .manager import _get_config, _assert_foreign_object_relations_allowed
        from .signals import pre_save, post_save
        import datetime
        cfg = _get_config(model=self.__class__, operation="write")
        _assert_foreign_object_relations_allowed(self)

        # ── Set auto_now fields ───────────────────────────────────────────
        for col in self._auto_now_cols:
            object.__setattr__(self, col, datetime.datetime.now())

        # ── MTI save: write parent table first, then child table ──────────
        if self._parent_model is not None:
            parent_model = self._parent_model
            parent_table = parent_model._get_table()
            parent_pk = parent_model._get_pk_column()
            ptr_col = self._ptr_col
            ptr_val = self.__dict__.get(ptr_col)
            created = ptr_val is None
            pre_save.send(sender=self.__class__, instance=self, created=created)
            with Connection(cfg) as conn:
                backend = conn.backend
                parent_cols = parent_model._fields
                skip_parent = {parent_pk} | set(getattr(parent_model, "_auto_now_add_cols", []))
                if ptr_val is None:
                    # INSERT parent
                    p_insert_cols = [c for c in parent_cols if c not in skip_parent]
                    p_data = [self.__dict__.get(c) for c in p_insert_cols]
                    sql, params = build_insert(backend, parent_table, p_insert_cols, p_data,
                                               returning=parent_pk)
                    rows = conn.execute(sql, params, as_dict=True)
                    if rows and parent_pk in rows[0]:
                        ptr_val = rows[0][parent_pk]
                        object.__setattr__(self, ptr_col, ptr_val)
                    # INSERT child
                    child_cols = [c for c in self._fields if c != ptr_col
                                  and c not in set(self._auto_now_add_cols)]
                    c_data = [self.__dict__.get(c) for c in child_cols]
                    sql, params = build_insert(
                        backend, self._get_table(),
                        [ptr_col] + child_cols, [ptr_val] + c_data,
                        returning=ptr_col,
                    )
                    conn.execute(sql, params, as_dict=True)
                else:
                    # UPDATE parent
                    p_set = {c: self.__dict__.get(c) for c in parent_cols
                             if c != parent_pk and c not in skip_parent}
                    if p_set:
                        sql, params = build_update(backend, parent_table, p_set, {parent_pk: ptr_val})
                        conn.execute(sql, params, as_dict=True)
                    # UPDATE child
                    c_set = {c: self.__dict__.get(c) for c in self._fields
                             if c != ptr_col and c not in set(self._auto_now_add_cols)}
                    if c_set:
                        sql, params = build_update(backend, self._get_table(), c_set, {ptr_col: ptr_val})
                        conn.execute(sql, params, as_dict=True)
            post_save.send(sender=self.__class__, instance=self, created=created)
            return

        # ── Normal save ───────────────────────────────────────────────────
        with Connection(cfg) as connection:
            backend = connection.backend
            table = self._get_table()
            pk_col = self._get_pk_column()
            columns = self._get_columns()
            data = {c: self.__dict__.get(c) for c in columns}
            pk_val = data.get(pk_col)
            created = pk_val is None
            pre_save.send(sender=self.__class__, instance=self, created=created)
            if pk_val is None:
                skip = {pk_col} | set(self._auto_now_add_cols)
                insert_cols = [c for c in columns if c not in skip]
                sql, params = build_insert(
                    backend, table, insert_cols,
                    [data[c] for c in insert_cols], returning=pk_col,
                )
                rows = connection.execute(sql, params, as_dict=True)
                if rows and pk_col in rows[0]:
                    object.__setattr__(self, pk_col, rows[0][pk_col])
            else:
                set_data = {k: v for k, v in data.items()
                            if k != pk_col and k not in self._auto_now_add_cols}
                if not set_data:
                    post_save.send(sender=self.__class__, instance=self, created=created)
                    return
                sql, params = build_update(backend, table, set_data, {pk_col: pk_val})
                connection.execute(sql, params, as_dict=True)
            post_save.send(sender=self.__class__, instance=self, created=created)

    async def asave(self) -> None:
        """Async INSERT or UPDATE using global connection. Handles MTI automatically."""
        from ..sql import build_insert, build_update
        from ..db.async_connection import AsyncConnection
        from .manager import _get_config, _assert_foreign_object_relations_allowed
        from .signals import pre_save, post_save
        import datetime
        cfg = _get_config(model=self.__class__, operation="write")
        _assert_foreign_object_relations_allowed(self)

        for col in self._auto_now_cols:
            object.__setattr__(self, col, datetime.datetime.now())

        if self._parent_model is not None:
            parent_model = self._parent_model
            parent_table = parent_model._get_table()
            parent_pk = parent_model._get_pk_column()
            ptr_col = self._ptr_col
            ptr_val = self.__dict__.get(ptr_col)
            created = ptr_val is None
            await pre_save.asend(sender=self.__class__, instance=self, created=created)
            async with AsyncConnection(cfg) as conn:
                backend = conn.backend
                parent_cols = parent_model._fields
                skip_parent = {parent_pk} | set(getattr(parent_model, "_auto_now_add_cols", []))
                if ptr_val is None:
                    p_insert_cols = [c for c in parent_cols if c not in skip_parent]
                    p_data = [self.__dict__.get(c) for c in p_insert_cols]
                    sql, params = build_insert(backend, parent_table, p_insert_cols, p_data,
                                               returning=parent_pk)
                    rows = await conn.execute(sql, params, as_dict=True)
                    if rows and parent_pk in rows[0]:
                        ptr_val = rows[0][parent_pk]
                        object.__setattr__(self, ptr_col, ptr_val)
                    child_cols = [c for c in self._fields if c != ptr_col
                                  and c not in set(self._auto_now_add_cols)]
                    c_data = [self.__dict__.get(c) for c in child_cols]
                    sql, params = build_insert(
                        backend, self._get_table(),
                        [ptr_col] + child_cols, [ptr_val] + c_data,
                        returning=ptr_col,
                    )
                    await conn.execute(sql, params, as_dict=True)
                else:
                    p_set = {c: self.__dict__.get(c) for c in parent_cols
                             if c != parent_pk and c not in skip_parent}
                    if p_set:
                        sql, params = build_update(backend, parent_table, p_set, {parent_pk: ptr_val})
                        await conn.execute(sql, params, as_dict=True)
                    c_set = {c: self.__dict__.get(c) for c in self._fields
                             if c != ptr_col and c not in set(self._auto_now_add_cols)}
                    if c_set:
                        sql, params = build_update(backend, self._get_table(), c_set, {ptr_col: ptr_val})
                        await conn.execute(sql, params, as_dict=True)
            await post_save.asend(sender=self.__class__, instance=self, created=created)
            return

        async with AsyncConnection(cfg) as connection:
            backend = connection.backend
            table = self._get_table()
            pk_col = self._get_pk_column()
            columns = self._get_columns()
            data = {c: self.__dict__.get(c) for c in columns}
            pk_val = data.get(pk_col)
            created = pk_val is None
            await pre_save.asend(sender=self.__class__, instance=self, created=created)
            if pk_val is None:
                skip = {pk_col} | set(self._auto_now_add_cols)
                insert_cols = [c for c in columns if c not in skip]
                sql, params = build_insert(
                    backend, table, insert_cols,
                    [data[c] for c in insert_cols], returning=pk_col,
                )
                rows = await connection.execute(sql, params, as_dict=True)
                if rows and pk_col in rows[0]:
                    object.__setattr__(self, pk_col, rows[0][pk_col])
            else:
                set_data = {k: v for k, v in data.items()
                            if k != pk_col and k not in self._auto_now_add_cols}
                if not set_data:
                    await post_save.asend(sender=self.__class__, instance=self, created=created)
                    return
                sql, params = build_update(backend, table, set_data, {pk_col: pk_val})
                await connection.execute(sql, params, as_dict=True)
            await post_save.asend(sender=self.__class__, instance=self, created=created)

    def delete(self) -> None:
        """DELETE this instance. Enforces on_delete at ORM level, then deletes from DB."""
        from ..sql.builder import build_delete
        from ..db.connection import Connection
        from .manager import _get_config
        from .signals import pre_delete, post_delete
        from .fields import CASCADE, PROTECT, RESTRICT
        pk_col = self._get_pk_column()
        pk_val = self.__dict__.get(pk_col)
        if pk_val is None:
            raise ValueError("Cannot delete an unsaved instance (no pk).")
        cfg = _get_config(model=self.__class__, operation="write")

        # ORM-level on_delete enforcement
        for model_cls in _MODEL_REGISTRY:
            if model_cls is self.__class__:
                continue
            for attr_name, rel in model_cls._relations.items():
                if rel.get("to") is not self.__class__:
                    continue
                fk_field = rel.get("field")
                fk_col = rel.get("column")
                on_delete = getattr(fk_field, "on_delete", CASCADE)
                if on_delete == CASCADE:
                    for row in model_cls.objects.filter(**{fk_col: pk_val}).all():
                        row.delete()
                elif on_delete in (PROTECT, RESTRICT):
                    count = model_cls.objects.filter(**{fk_col: pk_val}).count()
                    if count > 0:
                        raise ProtectedError(
                            f"Cannot delete {self.__class__.__name__} pk={pk_val}: "
                            f"{count} {model_cls.__name__} row(s) reference it "
                            f"via {attr_name} (on_delete={on_delete})"
                        )

        pre_delete.send(sender=self.__class__, instance=self)
        with Connection(cfg) as conn:
            backend = conn.backend
            # MTI: delete parent row (DB CASCADE removes child)
            if self._parent_model is not None:
                parent_table = self._parent_model._get_table()
                parent_pk = self._parent_model._get_pk_column()
                sql, params = build_delete(backend, parent_table, {parent_pk: pk_val})
            else:
                sql, params = build_delete(backend, self._get_table(), {pk_col: pk_val})
            conn.execute(sql, params, as_dict=True)
        post_delete.send(sender=self.__class__, instance=self)

    async def adelete(self) -> None:
        """Async DELETE. Enforces on_delete at ORM level, then deletes from DB."""
        from ..sql.builder import build_delete
        from .manager import _get_config, _use_async_conn
        from .signals import pre_delete, post_delete
        from .fields import CASCADE, PROTECT, RESTRICT
        pk_col = self._get_pk_column()
        pk_val = self.__dict__.get(pk_col)
        if pk_val is None:
            raise ValueError("Cannot delete an unsaved instance (no pk).")
        cfg = _get_config(model=self.__class__, operation="write")

        for model_cls in _MODEL_REGISTRY:
            if model_cls is self.__class__:
                continue
            for attr_name, rel in model_cls._relations.items():
                if rel.get("to") is not self.__class__:
                    continue
                fk_field = rel.get("field")
                fk_col = rel.get("column")
                on_delete = getattr(fk_field, "on_delete", CASCADE)
                if on_delete == CASCADE:
                    for row in await model_cls.objects.filter(**{fk_col: pk_val}).alist():
                        await row.adelete()
                elif on_delete in (PROTECT, RESTRICT):
                    count = await model_cls.objects.filter(**{fk_col: pk_val}).acount()
                    if count > 0:
                        raise ProtectedError(
                            f"Cannot delete {self.__class__.__name__} pk={pk_val}: "
                            f"{count} {model_cls.__name__} row(s) reference it "
                            f"via {attr_name} (on_delete={on_delete})"
                        )

        await pre_delete.asend(sender=self.__class__, instance=self)
        async with _use_async_conn(cfg) as conn:
            backend = conn.backend
            if self._parent_model is not None:
                parent_table = self._parent_model._get_table()
                parent_pk = self._parent_model._get_pk_column()
                sql, params = build_delete(backend, parent_table, {parent_pk: pk_val})
            else:
                sql, params = build_delete(backend, self._get_table(), {pk_col: pk_val})
            await conn.execute(sql, params, as_dict=True)
        await post_delete.asend(sender=self.__class__, instance=self)

    def __repr__(self) -> str:
        pk = self.__dict__.get(self._get_pk_column())
        return f"<{self.__class__.__name__} pk={pk}>"

M = TypeVar("M", bound=Model)


def table_name(model_class: Type[Model]) -> str:
    return model_class._get_table()


def column_names(model_class: Type[Model]) -> List[str]:
    return model_class._get_columns()


def pk_column(model_class: Type[Model]) -> str:
    return model_class._get_pk_column()
