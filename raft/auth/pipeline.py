"""
raft.auth.pipeline
~~~~~~~~~~~~~~~~~~

Shared authentication / permission runner used by class-based and function-based views.
"""

from __future__ import annotations

from typing import Any

from raft.core.exceptions import Forbidden, Unauthorized
from raft.core.request import RaftRequest


def instantiate_classes(classes: list[Any] | tuple[Any, ...] | None) -> list[Any]:
    """Instantiate auth/permission classes (accepts classes or instances)."""
    if not classes:
        return []
    out: list[Any] = []
    for item in classes:
        out.append(item() if isinstance(item, type) else item)
    return out


def perform_authentication(
    request: RaftRequest,
    authenticators: list[Any],
) -> None:
    """Try each authenticator; set ``request.user`` / ``request.auth``.

    First non-``None`` result wins. If none apply, user/auth stay anonymous.
    """
    request.user = None
    request.auth = None
    request.state["successful_authenticator"] = None

    for authenticator in authenticators:
        result = authenticator.authenticate(request)
        if result is None:
            continue
        user, auth = result
        request.user = user
        request.auth = auth
        request.state["user"] = user
        request.state["auth"] = auth
        request.state["successful_authenticator"] = authenticator
        return


def check_permissions(
    request: RaftRequest,
    permissions: list[Any],
    *,
    view: Any = None,
    authenticators: list[Any] | None = None,
) -> None:
    """Raise ``Unauthorized`` / ``Forbidden`` when a permission denies access."""
    if not permissions:
        return

    for permission in permissions:
        if permission.has_permission(request, view):
            continue
        message = getattr(permission, "message", None) or "Permission denied"
        # Unauthenticated user + failed IsAuthenticated → 401; else 403
        if authenticators and request.user is None:
            raise Unauthorized(message=message)
        if request.user is None:
            raise Unauthorized(message=message)
        raise Forbidden(message=message)


def run_auth_pipeline(
    request: RaftRequest,
    *,
    authentication_classes: list[Any] | tuple[Any, ...] | None = None,
    permission_classes: list[Any] | tuple[Any, ...] | None = None,
    view: Any = None,
) -> None:
    """Authenticate then check permissions (view ``initial`` hook equivalent)."""
    authenticators = instantiate_classes(authentication_classes)
    permissions = instantiate_classes(permission_classes)
    perform_authentication(request, authenticators)
    check_permissions(
        request,
        permissions,
        view=view,
        authenticators=authenticators,
    )
