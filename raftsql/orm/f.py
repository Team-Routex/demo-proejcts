"""
F objects — reference a model field in a query expression.

Usage:
    from raftsql import F

    # Compare two columns
    Product.objects.filter(stock__gt=F("reserved"))

    # Use in update (increment a column)
    Product.objects.filter(pk=1).update(views=F("views"))   # raw reference
"""


class F:
    """
    Reference to a database column. Used in filter expressions to compare
    a column against another column rather than a literal value.

        Product.objects.filter(price__gt=F("cost"))
        # → WHERE price > cost
    """

    def __init__(self, field: str) -> None:
        self.field = field

    def __repr__(self) -> str:
        return f"F({self.field!r})"
