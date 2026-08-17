"""
raft.auth.permissions
~~~~~~~~~~~~~~~~~~~~~

Permission classes for views.
"""

from __future__ import annotations

from typing import Any

from raft.core.request import RaftRequest


class BasePermission:
    """Base class for permission checks."""

    message: str | None = None

    def has_permission(self, request: RaftRequest, view: Any) -> bool:
        """Return True if access should be granted."""
        raise NotImplementedError("has_permission() must be implemented.")


class AllowAny(BasePermission):
    """Always allow access (default when ``permission_classes`` is empty)."""

    def has_permission(self, request: RaftRequest, view: Any) -> bool:
        return True


class IsAuthenticated(BasePermission):
    """Allow only requests with a non-anonymous ``request.user``."""

    message = "Authentication credentials were not provided."

    def has_permission(self, request: RaftRequest, view: Any) -> bool:
        user = getattr(request, "user", None)
        return user is not None
