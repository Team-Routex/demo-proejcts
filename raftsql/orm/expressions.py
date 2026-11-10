"""
Advanced SQL expressions: Window functions, COALESCE, Subquery, OuterRef.

Usage examples
──────────────

Window functions:
    from raftsql import Window, RowNumber, Rank, DenseRank, Lag, Lead
    from raftsql import FirstValue, LastValue, Sum

    # ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC)
    Employee.objects.annotate(
        row_num=Window(RowNumber(), partition_by=["dept"], order_by=["-salary"])
    ).all()

    # Running total per category
    Item.objects.annotate(
        running_total=Window(Sum("price"), partition_by=["category"], order_by=["created_at"])
    ).all()

    # LAG / LEAD
    Sale.objects.annotate(
        prev_amount=Window(Lag("amount", 1), order_by=["sale_date"])
    ).all()

COALESCE:
    from raftsql import Coalesce, Value

    # First non-NULL value
    User.objects.annotate(display_name=Coalesce("nickname", "username")).all()

    # With a literal default
    User.objects.annotate(label=Coalesce("nickname", Value("Anonymous"))).all()

Subquery / OuterRef:
    from raftsql import Subquery, OuterRef

    # Filter by subquery (id IN ...)
    active_author_ids = Post.objects.filter(published=True).values("author_id")
    User.objects.filter(id__in=Subquery(active_author_ids)).all()

    # Correlated subquery in annotate
    latest = Post.objects.filter(author_id=OuterRef("id")) \\
                         .order_by("-created_at").values("title").limit(1)
    User.objects.annotate(latest_post=Subquery(latest)).all()
"""
from typing import Any, List, Optional


# ── Window function expressions ───────────────────────────────────────────────

class WindowFunction:
    """
    Base for pure window functions (ROW_NUMBER, RANK, etc.).
    Used as the first argument to Window().
    """
    sql_function: str = ""

    def as_sql(self, backend: Any) -> str:
        return f"{self.sql_function}()"


class RowNumber(WindowFunction):
    """ROW_NUMBER() — unique sequential number per partition."""
    sql_function = "ROW_NUMBER"


class Rank(WindowFunction):
    """RANK() — rank with gaps on ties."""
    sql_function = "RANK"


class DenseRank(WindowFunction):
    """DENSE_RANK() — rank without gaps on ties."""
    sql_function = "DENSE_RANK"


class PercentRank(WindowFunction):
    """PERCENT_RANK() — relative rank as a fraction 0–1."""
    sql_function = "PERCENT_RANK"


class CumeDist(WindowFunction):
    """CUME_DIST() — cumulative distribution."""
    sql_function = "CUME_DIST"


class Ntile(WindowFunction):
    """NTILE(n) — divide rows into n buckets."""
    def __init__(self, n: int) -> None:
        self.n = int(n)

    def as_sql(self, backend: Any) -> str:
        return f"NTILE({self.n})"


class Lag(WindowFunction):
    """
    LAG(field, offset=1, default=None)
    Returns value from a previous row in the partition.
    """
    def __init__(self, field: str, offset: int = 1, default: Any = None) -> None:
        self.field = field
        self.offset = offset
        self.default = default

    def as_sql(self, backend: Any) -> str:
        q = backend.quote_ident
        parts = [q(self.field), str(self.offset)]
        if self.default is not None:
            parts.append(repr(self.default))
        return f"LAG({', '.join(parts)})"


class Lead(WindowFunction):
    """
    LEAD(field, offset=1, default=None)
    Returns value from a following row in the partition.
    """
    def __init__(self, field: str, offset: int = 1, default: Any = None) -> None:
        self.field = field
        self.offset = offset
        self.default = default

    def as_sql(self, backend: Any) -> str:
        q = backend.quote_ident
        parts = [q(self.field), str(self.offset)]
        if self.default is not None:
            parts.append(repr(self.default))
        return f"LEAD({', '.join(parts)})"


class FirstValue(WindowFunction):
    """FIRST_VALUE(field) — first value in window frame."""
    def __init__(self, field: str) -> None:
        self.field = field

    def as_sql(self, backend: Any) -> str:
        return f"FIRST_VALUE({backend.quote_ident(self.field)})"


class LastValue(WindowFunction):
    """LAST_VALUE(field) — last value in window frame."""
    def __init__(self, field: str) -> None:
        self.field = field

    def as_sql(self, backend: Any) -> str:
        return f"LAST_VALUE({backend.quote_ident(self.field)})"


class NthValue(WindowFunction):
    """NTH_VALUE(field, n) — n-th value in window frame."""
    def __init__(self, field: str, n: int) -> None:
        self.field = field
        self.n = int(n)

    def as_sql(self, backend: Any) -> str:
        return f"NTH_VALUE({backend.quote_ident(self.field)}, {self.n})"


# ── Window wrapper ────────────────────────────────────────────────────────────

class Window:
    """
    Wrap any expression (window function OR aggregate) in an OVER clause.

        Window(RowNumber(), partition_by=["dept"], order_by=["-salary"])
        Window(Sum("price"), partition_by=["category"], order_by=["date"])
        Window(Lag("price", 1), order_by=["date"])

    Parameters
    ----------
    expression   : WindowFunction or Aggregate — the function before OVER
    partition_by : list of column names for PARTITION BY
    order_by     : list of column names; prefix with '-' for DESC
    frame        : raw ROWS/RANGE clause string, e.g.
                   "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
    """

    def __init__(
        self,
        expression: Any,
        *,
        partition_by: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        frame: Optional[str] = None,
    ) -> None:
        self.expression = expression
        self.partition_by = partition_by or []
        self.order_by = order_by or []
        self.frame = frame

    def as_sql(self, backend: Any) -> str:
        q = backend.quote_ident
        expr_sql = self.expression.as_sql(backend)

        over_parts: List[str] = []

        if self.partition_by:
            cols = ", ".join(q(c) for c in self.partition_by)
            over_parts.append(f"PARTITION BY {cols}")

        if self.order_by:
            order_parts = []
            for col in self.order_by:
                if isinstance(col, str) and col.startswith("-"):
                    order_parts.append(f"{q(col[1:])} DESC")
                else:
                    order_parts.append(f"{q(str(col))} ASC")
            over_parts.append(f"ORDER BY {', '.join(order_parts)}")

        if self.frame:
            over_parts.append(self.frame)

        return f"{expr_sql} OVER ({' '.join(over_parts)})"

    def __repr__(self) -> str:
        return f"Window({self.expression!r})"


# ── COALESCE / Value ──────────────────────────────────────────────────────────

class Value:
    """
    A literal SQL value (rendered as a %s placeholder).

        Coalesce("nickname", Value("Anonymous"))
        # → COALESCE("nickname", %s)  with params: ["Anonymous"]
    """

    def __init__(self, value: Any) -> None:
        self.value = value

    def as_sql(self, backend: Any, params: List) -> str:
        params.append(self.value)
        return "%s"

    def __repr__(self) -> str:
        return f"Value({self.value!r})"


class Coalesce:
    """
    COALESCE(field1, field2, ...) — returns the first non-NULL value.

        # Column fallback
        User.objects.annotate(name=Coalesce("nickname", "username")).all()
        # → SELECT *, COALESCE("nickname", "username") AS "name" FROM users

        # Literal default
        User.objects.annotate(name=Coalesce("nickname", Value("Anonymous"))).all()
        # → SELECT *, COALESCE("nickname", %s) AS "name" FROM users  params=["Anonymous"]
    """

    def __init__(self, *fields: Any) -> None:
        if len(fields) < 2:
            raise ValueError("Coalesce requires at least 2 arguments.")
        self.fields = fields

    def as_sql(self, backend: Any, params: List) -> str:
        q = backend.quote_ident
        parts = []
        for field in self.fields:
            if isinstance(field, Value):
                parts.append(field.as_sql(backend, params))
            elif isinstance(field, str):
                parts.append(q(field))
            elif hasattr(field, "as_sql"):
                # Nested expression (Subquery, another Coalesce, etc.)
                sig = field.as_sql.__code__.co_varnames
                if "params" in sig:
                    parts.append(field.as_sql(backend, params))
                else:
                    parts.append(field.as_sql(backend))
            else:
                params.append(field)
                parts.append("%s")
        return f"COALESCE({', '.join(parts)})"

    def __repr__(self) -> str:
        return f"Coalesce{self.fields!r}"


# ── Subquery / OuterRef ───────────────────────────────────────────────────────

class OuterRef:
    """
    Reference to a column in the outer query for correlated subqueries.

        Post.objects.filter(author_id=OuterRef("id"))
        # Inside a Subquery → WHERE "posts"."author_id" = "users"."id"

    The outer table name is injected automatically when the Subquery is
    evaluated inside annotate() on the outer QuerySet.
    """

    def __init__(self, field: str) -> None:
        self.field = field

    def __repr__(self) -> str:
        return f"OuterRef({self.field!r})"


class Subquery:
    """
    Embed a QuerySet as a SQL subquery in a filter or annotation.

    In filter (IN):
        ids = Post.objects.filter(published=True).values("author_id")
        User.objects.filter(id__in=Subquery(ids)).all()
        # WHERE "id" IN (SELECT "posts"."author_id" FROM "posts" WHERE ...)

    In annotate (scalar correlated subquery):
        latest = (Post.objects
                  .filter(author_id=OuterRef("id"))
                  .order_by("-created_at").values("title").limit(1))
        User.objects.annotate(latest_post=Subquery(latest)).all()
        # SELECT *, (SELECT ... FROM posts WHERE author_id = users.id ...) AS latest_post
    """

    def __init__(self, queryset: Any) -> None:
        self.queryset = queryset
        self._outer_table: Optional[str] = None

    def resolve(self, outer_table: str) -> "Subquery":
        """Return a copy with the outer table name set (for OuterRef resolution)."""
        sq = Subquery.__new__(Subquery)
        sq.queryset = self.queryset
        sq._outer_table = outer_table
        return sq

    def as_sql(self, backend: Any, params: List) -> str:
        sql, sub_params = self.queryset._build_select_sql(
            backend, outer_table=self._outer_table
        )
        params.extend(sub_params)
        return f"({sql})"

    def __repr__(self) -> str:
        return f"Subquery({self.queryset!r})"


# ── CASE / WHEN ───────────────────────────────────────────────────────────────

class When:
    """
    A single WHEN … THEN … branch for use inside Case().

        When(in_stock=True, then=Value("Available"))
        When(price__gte=100, then=Value("Premium"))

    `condition` kwargs are the same lookup syntax as QuerySet.filter().
    `then` is the result — use Value() for a literal, or a field name string.
    """

    def __init__(self, then: Any, **condition_kwargs: Any) -> None:
        if not condition_kwargs:
            raise ValueError("When() requires at least one condition keyword argument.")
        self.condition_kwargs = condition_kwargs
        self.then = then

    def as_sql(self, backend: Any, params: List) -> str:
        from ..sql.where import build_where
        from .q import Q
        node = Q(**self.condition_kwargs)
        where_sql, where_params = build_where([node], backend)
        params.extend(where_params)

        # THEN value
        if isinstance(self.then, Value):
            then_sql = self.then.as_sql(backend, params)
        elif isinstance(self.then, str):
            then_sql = backend.quote_ident(self.then)
        elif isinstance(self.then, (int, float)):
            params.append(self.then)
            then_sql = "%s"
        elif hasattr(self.then, "as_sql"):
            then_sql = self.then.as_sql(backend, params)
        else:
            params.append(self.then)
            then_sql = "%s"

        return f"WHEN {where_sql} THEN {then_sql}"

    def __repr__(self) -> str:
        return f"When({self.condition_kwargs!r}, then={self.then!r})"


class Case:
    """
    CASE WHEN … THEN … [ELSE …] END — conditional expression in SELECT.

    Usage:
        from raftsql import Case, When, Value

        # Label items
        Item.objects.annotate(
            status=Case(
                When(in_stock=True,   then=Value("In Stock")),
                When(in_stock=False,  then=Value("Out of Stock")),
                default=Value("Unknown"),
            )
        ).all()

        # Numeric bucketing
        Item.objects.annotate(
            tier=Case(
                When(price__gte=100, then=Value("premium")),
                When(price__gte=50,  then=Value("mid")),
                default=Value("budget"),
            )
        ).all()
    """

    def __init__(self, *whens: "When", default: Any = None) -> None:
        if not whens:
            raise ValueError("Case() requires at least one When() branch.")
        self.whens = whens
        self.default = default

    def as_sql(self, backend: Any, params: List) -> str:
        parts = ["CASE"]
        for when in self.whens:
            parts.append(when.as_sql(backend, params))

        if self.default is not None:
            if isinstance(self.default, Value):
                default_sql = self.default.as_sql(backend, params)
            elif isinstance(self.default, str):
                default_sql = backend.quote_ident(self.default)
            elif isinstance(self.default, (int, float)):
                params.append(self.default)
                default_sql = "%s"
            elif hasattr(self.default, "as_sql"):
                default_sql = self.default.as_sql(backend, params)
            else:
                params.append(self.default)
                default_sql = "%s"
            parts.append(f"ELSE {default_sql}")

        parts.append("END")
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"Case({self.whens!r}, default={self.default!r})"


# ── Cast ──────────────────────────────────────────────────────────────────────

class Cast:
    """
    CAST(expression AS type) — explicit type casting.

    Usage:
        from raftsql import Cast

        # Cast a column to another type
        Item.objects.annotate(price_int=Cast("price", "INTEGER")).all()
        Item.objects.annotate(id_text=Cast("id", "TEXT")).all()

        # Nest inside other expressions
        Item.objects.annotate(
            label=Coalesce(Cast("price", "TEXT"), Value("N/A"))
        ).all()
    """

    def __init__(self, expression: Any, output_type: str) -> None:
        self.expression = expression
        self.output_type = output_type.upper()

    def as_sql(self, backend: Any, params: Optional[List] = None) -> str:
        if params is None:
            params = []
        q = backend.quote_ident
        if isinstance(self.expression, str):
            expr_sql = q(self.expression)
        elif isinstance(self.expression, Value):
            expr_sql = self.expression.as_sql(backend, params)
        elif hasattr(self.expression, "as_sql"):
            import inspect
            sig = inspect.signature(self.expression.as_sql)
            if "params" in sig.parameters:
                expr_sql = self.expression.as_sql(backend, params)
            else:
                expr_sql = self.expression.as_sql(backend)
        else:
            params.append(self.expression)
            expr_sql = "%s"
        return f"CAST({expr_sql} AS {self.output_type})"

    def __repr__(self) -> str:
        return f"Cast({self.expression!r}, {self.output_type!r})"
