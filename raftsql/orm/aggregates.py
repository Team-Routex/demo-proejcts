"""
Aggregate functions for use in .aggregate() and .annotate().

Usage:
    from raftsql import Count, Sum, Avg, Max, Min

    # aggregate() — execute immediately, return a dict
    result = Item.objects.filter(in_stock=True).aggregate(
        total   = Sum("price"),
        count   = Count("id"),
        average = Avg("price"),
        highest = Max("price"),
        lowest  = Min("price"),
    )
    # → {"total": 450.0, "count": 9, "average": 50.0, "highest": 120.0, "lowest": 10.0}

    # annotate() — add computed column to each row
    from raftsql import F
    Item.objects.values("category").annotate(total=Sum("price"))
    # → [{"category": "books", "total": 120.0}, ...]

    # Count with distinct
    User.objects.aggregate(unique_countries=Count("country", distinct=True))
"""
from typing import Any


class Aggregate:
    sql_function: str = ""

    def __init__(self, field: str = "*", *, distinct: bool = False) -> None:
        self.field = field
        self.distinct = distinct

    def as_sql(self, backend: Any) -> str:
        """Return the SQL expression, e.g. COUNT(DISTINCT "price")."""
        q = backend.quote_ident
        distinct = "DISTINCT " if self.distinct else ""
        field_sql = "*" if self.field == "*" else q(self.field)
        return f"{self.sql_function}({distinct}{field_sql})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.field!r})"


class Count(Aggregate):
    """COUNT(*) or COUNT(field) or COUNT(DISTINCT field)."""
    sql_function = "COUNT"

    def __init__(self, field: str = "*", **kwargs: Any) -> None:
        super().__init__(field, **kwargs)


class Sum(Aggregate):
    """SUM(field)."""
    sql_function = "SUM"


class Avg(Aggregate):
    """AVG(field)."""
    sql_function = "AVG"


class Max(Aggregate):
    """MAX(field)."""
    sql_function = "MAX"


class Min(Aggregate):
    """MIN(field)."""
    sql_function = "MIN"
