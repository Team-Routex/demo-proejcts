"""
Django-style Field classes: scalar fields + relation fields (ForeignKey, OneToOneField, ManyToManyField).
"""
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .model import Model


# --- on_delete choices ---
CASCADE = "CASCADE"
SET_NULL = "SET NULL"
PROTECT = "PROTECT"
RESTRICT = "RESTRICT"
DO_NOTHING = "DO NOTHING"


# --- Base ---

class Field:
    """Base scalar field.

    Common keyword arguments (all optional, keyword-only):
        primary_key (bool)        – mark this column as the PRIMARY KEY
        null        (bool)        – allow NULL in the database column
        blank       (bool)        – allow empty values at the application level
        unique      (bool)        – add a UNIQUE constraint
        default     (Any)         – default value; use "CURRENT_TIMESTAMP" for datetime defaults
        db_column   (str | None)  – override the generated column name
    """

    primary_key: bool = False
    db_column: Optional[str] = None

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        self.primary_key = primary_key
        self.null = null
        self.blank = blank
        self.unique = unique
        self.db_index = db_index
        self.default = default
        self.db_column = db_column

    def get_sql_type(self) -> str:
        return "TEXT"

    def get_column_sql(self) -> str:
        parts = [self.get_sql_type()]
        if not self.null:
            parts.append("NOT NULL")
        if self.unique:
            parts.append("UNIQUE")
        if self.default is not None:
            if isinstance(self.default, str) and self.default.upper() in ("CURRENT_TIMESTAMP", "NOW()"):
                parts.append(f"DEFAULT {self.default}")
            else:
                parts.append(f"DEFAULT {repr(self.default)}")
        return " ".join(parts)


# --- Scalar fields ---

class AutoField(Field):
    """Auto-increment integer primary key (SERIAL PRIMARY KEY)."""

    def __init__(
        self,
        *,
        primary_key: bool = True,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "SERIAL PRIMARY KEY"

    def get_column_sql(self) -> str:
        return self.get_sql_type()


class IntegerField(Field):
    """INTEGER column."""

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Optional[int] = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "INTEGER"


class BigIntegerField(Field):
    """BIGINT column."""

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Optional[int] = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "BIGINT"


class FloatField(Field):
    """FLOAT column."""

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Optional[float] = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "FLOAT"


class DecimalField(Field):
    """NUMERIC(max_digits, decimal_places) column."""

    def __init__(
        self,
        *,
        max_digits: int = 10,
        decimal_places: int = 2,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )
        self.max_digits = max_digits
        self.decimal_places = decimal_places

    def get_sql_type(self) -> str:
        return f"NUMERIC({self.max_digits}, {self.decimal_places})"


class CharField(Field):
    """VARCHAR(max_length) column."""

    def __init__(
        self,
        *,
        max_length: int = 255,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Optional[str] = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )
        self.max_length = max_length

    def get_sql_type(self) -> str:
        return f"VARCHAR({self.max_length})"


class TextField(Field):
    """TEXT column."""

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Optional[str] = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "TEXT"


class EmailField(Field):
    """VARCHAR(max_length) column validated as an e-mail address."""

    def __init__(
        self,
        *,
        max_length: int = 255,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Optional[str] = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )
        self.max_length = max_length

    def get_sql_type(self) -> str:
        return f"VARCHAR({self.max_length})"


class BooleanField(Field):
    """BOOLEAN column."""

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Optional[bool] = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "BOOLEAN"


class DateField(Field):
    """DATE column."""

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "DATE"


class DateTimeField(Field):
    """TIMESTAMP column.

    Extra keyword arguments:
        auto_now_add (bool) – set DEFAULT CURRENT_TIMESTAMP on the column;
                              the column is populated automatically on INSERT.
        auto_now     (bool) – update the value on every save (application-level).
    """

    def __init__(
        self,
        *,
        auto_now_add: bool = False,
        auto_now: bool = False,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        if auto_now_add and auto_now:
            raise ValueError("Cannot use both auto_now_add and auto_now")
        self.auto_now_add = auto_now_add
        self.auto_now = auto_now
        if auto_now_add and default is None:
            default = "CURRENT_TIMESTAMP"
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "TIMESTAMP"


class JSONField(Field):
    """JSONB column (PostgreSQL)."""

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )


# --- Relation fields ---

class RelationField(Field):
    """Base for relation fields."""
    is_relation: bool = True
    many_to_many: bool = False
    one_to_one: bool = False

    def __init__(
        self,
        to: Any,
        *,
        on_delete: str = CASCADE,
        related_name: Optional[str] = None,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            null=null,
            blank=blank,
            unique=unique,
            default=default,
            db_column=db_column,
        )
        self.to = to
        self.on_delete = on_delete
        self.related_name = related_name


class ForeignKey(RelationField):
    """Many-to-one relation.

    Creates an INTEGER column ``{attr_name}_id`` on this model's table.

    Args:
        to          : the related Model class
        on_delete   : CASCADE | SET_NULL | PROTECT | DO_NOTHING  (default CASCADE)
        related_name: reverse accessor name on the related model (optional)
        null        : allow NULL in the FK column
        blank       : allow empty at application level
        unique      : add UNIQUE constraint (prefer OneToOneField for 1:1)
        db_column   : override the generated ``{attr_name}_id`` column name
    """

    def __init__(
        self,
        to: Any,
        *,
        on_delete: str = CASCADE,
        related_name: Optional[str] = None,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            to=to,
            on_delete=on_delete,
            related_name=related_name,
            null=null,
            blank=blank,
            unique=unique,
            default=default,
            db_column=db_column,
        )

    def get_column_name(self, attr_name: str) -> str:
        if self.db_column:
            return self.db_column
        return f"{attr_name}_id"

    def get_sql_type(self) -> str:
        return "INTEGER"

    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        if obj is None:
            return self
        col = self.get_column_name(self._attr_name)
        fk_value = obj.__dict__.get(col)
        cache_key = f"_related_{self._attr_name}"
        cached = obj.__dict__.get(cache_key)
        if cached is not None:
            return cached
        try:
            from .manager import _get_config
            from ..db.connection import Connection
            from ..sql.builder import build_select
            cfg = _get_config(model=self.to, operation="read")
            if fk_value is not None:
                with Connection(cfg) as conn:
                    backend = conn.backend
                    table = self.to._get_table()
                    columns = self.to._get_columns()
                    pk_col = self.to._get_pk_column()
                    sql, params = build_select(backend, table, columns, where={pk_col: fk_value}, limit=1)
                    rows = conn.execute(sql, params, as_dict=True)
                    if rows:
                        instance = self.to.from_row(dict(rows[0]))
                        obj.__dict__[cache_key] = instance
                        return instance
            return None
        except RuntimeError:
            from .relations import RelatedAccessor
            return RelatedAccessor(obj, self.to, fk_value)


class OneToOneField(ForeignKey):
    """One-to-one relation — like ForeignKey but enforces UNIQUE.

    Args:
        to          : the related Model class
        on_delete   : CASCADE | SET_NULL | PROTECT | DO_NOTHING  (default CASCADE)
        related_name: reverse accessor name on the related model (optional)
        null        : allow NULL in the FK column
        blank       : allow empty at application level
        db_column   : override the generated ``{attr_name}_id`` column name
    """
    one_to_one: bool = True

    def __init__(
        self,
        to: Any,
        *,
        on_delete: str = CASCADE,
        related_name: Optional[str] = None,
        null: bool = False,
        blank: bool = True,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            to=to,
            on_delete=on_delete,
            related_name=related_name,
            null=null,
            blank=blank,
            unique=True,        # always UNIQUE for 1:1
            default=default,
            db_column=db_column,
        )

    def get_column_sql(self) -> str:
        parts = [self.get_sql_type()]
        if not self.null:
            parts.append("NOT NULL")
        parts.append("UNIQUE")
        return " ".join(parts)


class ManyToManyField(RelationField):
    """Many-to-many relation — no column on this model's table.

    Creates a junction table ``{model_a}_{model_b}`` with
    ``{model_a}_id`` and ``{model_b}_id`` columns.

    Args:
        to           : the related Model class
        through      : explicit junction table name (default: auto-generated)
        related_name : reverse accessor name on the related model (optional)
    """
    many_to_many: bool = True
    is_relation: bool = True

    def __init__(
        self,
        to: Any,
        *,
        through: Optional[str] = None,
        related_name: Optional[str] = None,
        null: bool = False,
        blank: bool = True,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            to=to,
            on_delete=DO_NOTHING,
            related_name=related_name,
            null=null,
            blank=blank,
            db_column=db_column,
        )
        self.through = through

    def get_junction_table(self, model_a_table: str, model_b_table: str) -> str:
        if self.through is not None:
            if isinstance(self.through, str):
                return self.through
            # Model class — use its table
            return self.through._get_table()
        tables = sorted([model_a_table, model_b_table])
        return f"{tables[0]}_{tables[1]}"

    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        if obj is None:
            return self
        from .relations import ManyToManyAccessor
        src_table = type(obj)._get_table()
        dst_table = self.to._get_table()

        if self.through is not None and not isinstance(self.through, str):
            # Explicit through model class — discover src/dst FK columns
            through_model = self.through
            junction = through_model._get_table()
            src_col, dst_col = None, None
            for _attr, rel in getattr(through_model, "_relations", {}).items():
                to_cls = rel.get("to")
                if not isinstance(to_cls, type):
                    continue
                rel_table = to_cls._get_table()
                if rel_table == src_table:
                    src_col = rel["column"]
                elif rel_table == dst_table:
                    dst_col = rel["column"]
            src_col = src_col or f"{src_table}_id"
            dst_col = dst_col or f"{dst_table}_id"
        else:
            junction = self.get_junction_table(src_table, dst_table)
            src_col = f"{src_table}_id"
            dst_col = f"{dst_table}_id"

        return ManyToManyAccessor(obj, self.to, junction, src_col, dst_col)


# ── New / extended field types ────────────────────────────────────────────────

class UUIDField(Field):
    """UUID column (PostgreSQL native UUID type).

    Stores 128-bit universally unique identifiers.
    Typical usage: ``id = UUIDField(primary_key=True, default="gen_random_uuid()")``
    """

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "UUID"

    def get_column_sql(self) -> str:
        parts = [self.get_sql_type()]
        if not self.null:
            parts.append("NOT NULL")
        if self.unique:
            parts.append("UNIQUE")
        if self.default is not None:
            dv = str(self.default)
            # Allow SQL function defaults like gen_random_uuid() / uuid_generate_v4()
            if dv.lower().endswith("()"):
                parts.append(f"DEFAULT {dv}")
            else:
                parts.append(f"DEFAULT {repr(dv)}")
        return " ".join(parts)


class TimeField(Field):
    """TIME column — stores a time-of-day value without date or timezone."""

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "TIME"


class SmallIntegerField(Field):
    """SMALLINT column (−32 768 to 32 767)."""

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Optional[int] = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "SMALLINT"


class PositiveIntegerField(Field):
    """INTEGER column with a CHECK constraint requiring the value >= 0.

    The ModelMeta calls ``generate_column_sql(column_name)`` so the CHECK
    can reference the actual column name (e.g. ``CHECK ("quantity" >= 0)``).
    """

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Optional[int] = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "INTEGER"

    def get_column_sql(self) -> str:
        # Fallback without column name — omits the CHECK constraint
        return super().get_column_sql()

    def generate_column_sql(self, column_name: str) -> str:
        """Called by ModelMeta so the CHECK can reference the actual column."""
        parts = ["INTEGER"]
        if not self.null:
            parts.append("NOT NULL")
        if self.unique:
            parts.append("UNIQUE")
        if self.default is not None:
            parts.append(f"DEFAULT {repr(self.default)}")
        parts.append(f'CHECK ("{column_name}" >= 0)')
        return " ".join(parts)


class SlugField(Field):
    """VARCHAR(max_length) optimised for URL slugs (default max_length=50)."""

    def __init__(
        self,
        *,
        max_length: int = 50,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = True,   # slugs are commonly looked up by exact match
        default: Optional[str] = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )
        self.max_length = max_length

    def get_sql_type(self) -> str:
        return f"VARCHAR({self.max_length})"


class BinaryField(Field):
    """BYTEA column (PostgreSQL) — stores raw binary data."""

    def __init__(
        self,
        *,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    def get_sql_type(self) -> str:
        return "BYTEA"


class ArrayField(Field):
    """PostgreSQL ARRAY column.

    Args:
        base_field : a Field instance whose SQL type defines the array element type.
                     E.g. ``ArrayField(IntegerField())`` → ``INTEGER[]``
        dimensions : number of array dimensions (default 1).

    Example::

        tags        = ArrayField(CharField(max_length=50))          # TEXT[] effectively
        matrix      = ArrayField(IntegerField(), dimensions=2)       # INTEGER[][]
    """

    def __init__(
        self,
        base_field: "Field",
        *,
        dimensions: int = 1,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )
        self.base_field = base_field
        self.dimensions = dimensions

    def get_sql_type(self) -> str:
        base = self.base_field.get_sql_type()
        return base + "[]" * self.dimensions


# ── Constraint helpers ────────────────────────────────────────────────────────

def _q_to_inline_sql(q_obj: Any, backend: Any = None) -> str:
    """Convert a Q object to a non-parameterized SQL string (for CHECK constraints)."""
    from ..sql.where import _build_q

    class _DummyBackend:
        def quote_ident(self, name: str) -> str:
            return f'"{name}"'

    _b = backend if backend is not None else _DummyBackend()
    params: list = []
    sql = _build_q(q_obj, _b, params)
    for p in params:
        if isinstance(p, bool):
            replacement = "TRUE" if p else "FALSE"
        elif p is None:
            replacement = "NULL"
        elif isinstance(p, str):
            replacement = "'{}'".format(p.replace("'", "''"))
        else:
            replacement = str(p)
        sql = sql.replace("%s", replacement, 1)
    return sql


class CheckConstraint:
    """Table-level CHECK constraint declared in ``class Meta: constraints = [...]``.

    Args:
        check: A Q object or a raw SQL expression string, e.g. ``Q(price__gt=0)``
               or ``"price > 0"``.
        name:  Unique constraint name (used in DDL and migration state).
    """

    def __init__(self, *, check: Any, name: str) -> None:
        self.check = check
        self.name = name

    def as_sql(self, backend: Any = None) -> str:
        from .q import Q
        if isinstance(self.check, str):
            expr = self.check
        elif isinstance(self.check, Q):
            expr = _q_to_inline_sql(self.check, backend)
        else:
            raise TypeError(f"check must be a Q or SQL string, got {type(self.check)}")
        return f'CONSTRAINT "{self.name}" CHECK ({expr})'

    def __repr__(self) -> str:
        return f"CheckConstraint(check={self.check!r}, name={self.name!r})"


class UniqueConstraint:
    """Table-level UNIQUE constraint declared in ``class Meta: constraints = [...]``.

    Args:
        fields:    List of field (column) names that form the unique key.
        name:      Unique constraint name.
        condition: Optional Q object for a partial unique constraint (WHERE clause).
    """

    def __init__(self, *, fields: list, name: str, condition: Any = None) -> None:
        self.fields = list(fields)
        self.name = name
        self.condition = condition

    def as_sql(self, backend: Any = None) -> str:
        if backend is not None:
            cols = ", ".join(backend.quote_ident(f) for f in self.fields)
        else:
            cols = ", ".join(f'"{f}"' for f in self.fields)
        sql = f'CONSTRAINT "{self.name}" UNIQUE ({cols})'
        if self.condition is not None:
            where_part = _q_to_inline_sql(self.condition, backend)
            sql += f" WHERE ({where_part})"
        return sql

    def __repr__(self) -> str:
        return f"UniqueConstraint(fields={self.fields!r}, name={self.name!r})"


# ── File / Image fields ───────────────────────────────────────────────────────

class FieldFile:
    """
    Proxy object returned when accessing a FileField attribute on a model instance.

    Wraps the raw path string stored in the database and provides:
        .name   – the stored relative path (e.g. ``"uploads/photo.jpg"``)
        .url    – the full URL via the field's storage backend
        .save(name, content) – write a new file and update the field
        .delete()            – remove the file from storage
    """

    def __init__(self, instance: Any, field: "FileField", name: Optional[str]) -> None:
        self.instance = instance
        self.field = field
        self.name = name
        self.storage = field.storage

    @property
    def url(self) -> str:
        if not self.name:
            return ""
        return self.storage.url(self.name)

    def save(self, name: str, content: Any, save_instance: bool = True) -> None:
        """Save *content* under *name* through the storage backend."""
        import os
        upload_to = self.field.upload_to
        if callable(upload_to):
            name = upload_to(self.instance, name)
        elif upload_to:
            name = os.path.join(upload_to, os.path.basename(name))
        self.name = self.storage.save(name, content)
        setattr(self.instance, self.field._attr_name, self.name)
        if save_instance:
            self.instance.save()

    def delete(self, save_instance: bool = True) -> None:
        """Delete the file from storage."""
        if self.name:
            self.storage.delete(self.name)
            self.name = None
            setattr(self.instance, self.field._attr_name, None)
            if save_instance:
                self.instance.save()

    def __bool__(self) -> bool:
        return bool(self.name)

    def __str__(self) -> str:
        return self.name or ""

    def __repr__(self) -> str:
        return f"<FieldFile: {self.name or 'empty'}>"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, FieldFile):
            return self.name == other.name
        return self.name == other


def _extract_upload(value: Any):
    """
    Extract ``(filename, BytesIO)`` from any framework's upload object.

    Supports:
    - FastAPI / Starlette  ``UploadFile``  (.filename + .file)
    - Flask / Werkzeug     ``FileStorage`` (.filename + .stream)
    - Django               ``InMemoryUploadedFile`` (.name + .read())
    - Plain                ``io.BytesIO`` / any file-like with .read()
    - Raw                  ``bytes`` / ``bytearray``
    """
    import io as _io
    import os as _os

    # FastAPI / Starlette: UploadFile has .filename and .file (SpooledTemporaryFile)
    if hasattr(value, "filename") and hasattr(value, "file"):
        name = value.filename or "upload"
        data = value.file.read()
        if hasattr(value.file, "seek"):
            value.file.seek(0)
        return _os.path.basename(name), _io.BytesIO(data)

    # Flask / Werkzeug: FileStorage has .filename and .stream
    if hasattr(value, "filename") and hasattr(value, "stream"):
        name = value.filename or "upload"
        data = value.stream.read()
        if hasattr(value.stream, "seek"):
            value.stream.seek(0)
        return _os.path.basename(name), _io.BytesIO(data)

    # Django InMemoryUploadedFile / any named file-like with .read()
    if hasattr(value, "name") and hasattr(value, "read"):
        raw_name = value.name or "upload"
        name = _os.path.basename(raw_name) if raw_name else "upload"
        data = value.read()
        if hasattr(value, "seek"):
            value.seek(0)
        return name, _io.BytesIO(data)

    # Plain file-like (io.BytesIO, io.FileIO, etc.)
    if hasattr(value, "read"):
        data = value.read()
        if hasattr(value, "seek"):
            value.seek(0)
        return "upload", _io.BytesIO(data)

    # Raw bytes / bytearray
    if isinstance(value, (bytes, bytearray)):
        return "upload", _io.BytesIO(bytes(value))

    raise TypeError(
        f"Cannot save {type(value).__name__!r} as a file. "
        f"Expected a file-like object (UploadFile, FileStorage, BytesIO, …) "
        f"or a string path."
    )


class FileField(Field):
    """VARCHAR(max_length) column that stores a file path.

    The file itself is persisted through a *storage* backend
    (default: ``FileSystemStorage`` reading ``MEDIA_ROOT`` / ``MEDIA_URL``
    from ``setraft.py``).

    Direct assignment of any upload object is supported — the file is saved
    to storage immediately and only the resulting path string is kept::

        blog.thumbnail = upload_file   # FastAPI UploadFile, Flask FileStorage, …
        blog.save()                    # only a path string hits the DB

    Args:
        upload_to  : Subdirectory (string) or callable ``fn(instance, filename) → path``
                     that determines where the file is stored.
        max_length : Column width (default 255).
        storage    : Custom :class:`raftsql.storage.Storage` instance.
                     Defaults to the module-level ``default_storage``.
    """

    def __init__(
        self,
        *,
        upload_to: Any = "",
        max_length: int = 255,
        storage: Any = None,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )
        self.upload_to = upload_to
        self.max_length = max_length
        self._storage = storage  # may be None → resolved lazily

    @property
    def storage(self) -> Any:
        if self._storage is not None:
            return self._storage
        from ..storage import default_storage
        return default_storage

    def get_sql_type(self) -> str:
        return f"VARCHAR({self.max_length})"

    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        if obj is None:
            return self
        raw = obj.__dict__.get(self._attr_name)
        return FieldFile(obj, self, raw)

    def __set__(self, obj: Any, value: Any) -> None:
        if value is None or isinstance(value, str):
            obj.__dict__[self._attr_name] = value
        elif isinstance(value, FieldFile):
            obj.__dict__[self._attr_name] = value.name
        else:
            # Any upload object (UploadFile, FileStorage, BytesIO, bytes…)
            # → save to storage now; store only the resulting path string.
            import os
            name, content = _extract_upload(value)
            upload_to = self.upload_to
            if callable(upload_to):
                name = upload_to(obj, name)
            elif upload_to:
                name = os.path.join(upload_to, os.path.basename(name))
            obj.__dict__[self._attr_name] = self.storage.save(name, content)


class ImageField(FileField):
    """Like :class:`FileField` but validates the uploaded content is a valid image.

    Requires Pillow to be installed (``pip install Pillow``).
    If Pillow is not available, the field behaves identically to ``FileField``
    (no image validation is performed).

    Args:
        upload_to  : Subdirectory string or callable (same as FileField).
        max_length : Column width (default 255).
        storage    : Custom storage backend (same as FileField).
    """

    def __init__(
        self,
        *,
        upload_to: Any = "",
        max_length: int = 255,
        storage: Any = None,
        primary_key: bool = False,
        null: bool = False,
        blank: bool = True,
        unique: bool = False,
        db_index: bool = False,
        default: Any = None,
        db_column: Optional[str] = None,
    ) -> None:
        super().__init__(
            upload_to=upload_to,
            max_length=max_length,
            storage=storage,
            primary_key=primary_key,
            null=null,
            blank=blank,
            unique=unique,
            db_index=db_index,
            default=default,
            db_column=db_column,
        )

    @staticmethod
    def _validate_image(content: Any) -> None:
        """Raise ValueError if *content* is not a valid image (requires Pillow)."""
        try:
            from PIL import Image
        except ImportError:
            return  # Pillow not installed → skip validation

        import io
        if hasattr(content, "read"):
            data = content.read()
            if hasattr(content, "seek"):
                content.seek(0)  # rewind so the storage backend can read it again
        elif isinstance(content, (bytes, bytearray)):
            data = bytes(content)
        else:
            return  # unknown type — skip

        try:
            img = Image.open(io.BytesIO(data))
            img.verify()  # raises if not a valid image
        except Exception as exc:
            raise ValueError(f"Upload is not a valid image: {exc}") from exc

    def __set__(self, obj: Any, value: Any) -> None:
        if value is None or isinstance(value, str):
            obj.__dict__[self._attr_name] = value
        elif isinstance(value, FieldFile):
            obj.__dict__[self._attr_name] = value.name
        else:
            # Extract once, validate with Pillow, then save.
            import os
            name, content = _extract_upload(value)
            self._validate_image(content)
            content.seek(0)
            upload_to = self.upload_to
            if callable(upload_to):
                name = upload_to(obj, name)
            elif upload_to:
                name = os.path.join(upload_to, os.path.basename(name))
            obj.__dict__[self._attr_name] = self.storage.save(name, content)

