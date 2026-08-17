"""
raft.auth.decorators
~~~~~~~~~~~~~~~~~~~~

``@authentication_classes`` / ``@permission_classes`` for function-based views.

Decorators set attributes and wrap the view once (safe to stack in either order)::

    @authentication_classes([JWTAuthentication])
    @permission_classes([IsAuthenticated])
    async def me(request):
        ...
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Sequence
from typing import Any

from raft.auth.pipeline import run_auth_pipeline
from raft.core.request import RaftRequest


def _wrap_with_auth_pipeline(func: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(func, "_raft_auth_wrapped", False):
        return func

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(request: RaftRequest, *args: Any, **kwargs: Any) -> Any:
            run_auth_pipeline(
                request,
                authentication_classes=getattr(async_wrapper, "authentication_classes", None),
                permission_classes=getattr(async_wrapper, "permission_classes", None),
                view=func,
            )
            return await func(request, *args, **kwargs)

        wrapped: Callable[..., Any] = async_wrapper
    else:

        @functools.wraps(func)
        def sync_wrapper(request: RaftRequest, *args: Any, **kwargs: Any) -> Any:
            run_auth_pipeline(
                request,
                authentication_classes=getattr(sync_wrapper, "authentication_classes", None),
                permission_classes=getattr(sync_wrapper, "permission_classes", None),
                view=func,
            )
            return func(request, *args, **kwargs)

        wrapped = sync_wrapper

    wrapped._raft_auth_wrapped = True  # type: ignore[attr-defined]
    wrapped.authentication_classes = getattr(func, "authentication_classes", None)  # type: ignore[attr-defined]
    wrapped.permission_classes = getattr(func, "permission_classes", None)  # type: ignore[attr-defined]
    return wrapped


def apply_view_auth(
    func: Callable[..., Any],
    *,
    authentication_classes: Sequence[Any] | None = None,
    permission_classes: Sequence[Any] | None = None,
) -> Callable[..., Any]:
    """Wrap *func* with the auth pipeline when class lists are provided.

    Used by ``@router.get(..., authentication_classes=...)`` and table ``route()``.
    """
    if not authentication_classes and not permission_classes:
        return func

    wrapped = _wrap_with_auth_pipeline(func)
    if authentication_classes is not None:
        wrapped.authentication_classes = list(authentication_classes)  # type: ignore[attr-defined]
    elif getattr(func, "authentication_classes", None) is not None:
        wrapped.authentication_classes = list(func.authentication_classes)  # type: ignore[attr-defined]
    if permission_classes is not None:
        wrapped.permission_classes = list(permission_classes)  # type: ignore[attr-defined]
    elif getattr(func, "permission_classes", None) is not None:
        wrapped.permission_classes = list(func.permission_classes)  # type: ignore[attr-defined]
    return wrapped


def authentication_classes(
    classes: Sequence[Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Set authentication classes on a function-based view."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if getattr(func, "_raft_auth_wrapped", False):
            func.authentication_classes = list(classes)  # type: ignore[attr-defined]
            return func
        func.authentication_classes = list(classes)  # type: ignore[attr-defined]
        return _wrap_with_auth_pipeline(func)

    return decorator


def permission_classes(
    classes: Sequence[Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Set permission classes on a function-based view."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if getattr(func, "_raft_auth_wrapped", False):
            func.permission_classes = list(classes)  # type: ignore[attr-defined]
            return func
        func.permission_classes = list(classes)  # type: ignore[attr-defined]
        return _wrap_with_auth_pipeline(func)

    return decorator
