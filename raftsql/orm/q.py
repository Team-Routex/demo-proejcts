"""
Q objects — compose complex WHERE conditions with AND / OR / NOT.

Usage:
    from raftsql import Q

    # AND (default when chaining .filter())
    User.objects.filter(Q(is_active=True) & Q(age__gte=18))

    # OR
    User.objects.filter(Q(name="Alice") | Q(name="Bob"))

    # NOT
    User.objects.filter(~Q(is_active=False))

    # Nested
    User.objects.filter(Q(country="US") | (Q(age__gte=18) & Q(is_verified=True)))
"""


class Q:
    AND = "AND"
    OR = "OR"

    def __init__(self, *q_objects: "Q", **kwargs):
        """
        Q(**kwargs)                 — one or more equality / lookup conditions
        Q(Q(...), Q(...))           — combine existing Q objects
        Q(Q(...), field=value, ...) — mix both
        """
        self.children: list = []
        self.connector: str = Q.AND
        self.negated: bool = False

        for q in q_objects:
            self.children.append(q)
        for key, value in kwargs.items():
            self.children.append((key, value))

    # ---- Operators ----

    def _combine(self, other: "Q", connector: str) -> "Q":
        obj = Q.__new__(Q)
        obj.children = [self, other]
        obj.connector = connector
        obj.negated = False
        return obj

    def __or__(self, other: "Q") -> "Q":
        return self._combine(other, Q.OR)

    def __and__(self, other: "Q") -> "Q":
        return self._combine(other, Q.AND)

    def __invert__(self) -> "Q":
        """~Q(...) — negate the condition."""
        obj = Q.__new__(Q)
        obj.children = list(self.children)
        obj.connector = self.connector
        obj.negated = not self.negated
        return obj

    def __bool__(self) -> bool:
        return bool(self.children)

    def __repr__(self) -> str:
        prefix = "NOT " if self.negated else ""
        inner = f" {self.connector} ".join(str(c) for c in self.children)
        return f"{prefix}Q({inner})"
