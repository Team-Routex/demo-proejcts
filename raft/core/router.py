"""
raft.core.router
~~~~~~~~~~~~~~~~

Hybrid routing system: supports both **decorator-style** and
**URL-conf style** (Django-like) route registration.

Decorator style::

    router = Router()

    @router.route("/users", methods=["GET"])
    async def list_users(request):
        ...

URL-conf style::

    from raft.core.router import Router, Route

    router = Router()
    router.add_routes([
        Route("/users", list_users, methods=["GET"]),
        Route("/users/{id}", get_user, methods=["GET"]),
    ])

Routers can be **nested** for modular apps::

    api_router = Router(prefix="/api")
    api_router.include_router(users_router)
    app.include_router(api_router)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.core.views import View


# Type alias for a view callable (FBV).
ViewCallable = Callable[[RaftRequest], Awaitable[RawResponse]]


@dataclass
class Route:
    """A single URL → handler mapping.

    Parameters:
        path: URL pattern, e.g. ``/users/{id}``.  Path parameters use
              ``{name}`` syntax and are converted to regex groups.
        handler: Async callable ``(RaftRequest) -> RawResponse``.
        methods: Allowed HTTP methods.  If ``None``, all methods match.
        name: Optional route name (useful for reverse lookups later).
        tags: OpenAPI tags for grouping in Swagger UI / ReDoc.
        summary: Short summary shown as the operation title in docs.
        request_body: Pydantic ``BaseModel`` subclass for the request body schema.
        responses: Dict of ``{status_code: description_or_model}`` for response docs.
    """

    path: str
    handler: ViewCallable
    methods: list[str] | None = None
    name: str | None = None

    # OpenAPI metadata — all optional
    tags: list[str] | None = None
    summary: str | None = None
    request_body: type | None = None  # Pydantic BaseModel subclass
    responses: dict[int, Any] | None = None

    # Compiled regex is populated by __post_init__.
    _pattern: re.Pattern[str] = field(default=None, repr=False)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.methods:
            self.methods = [m.upper() for m in self.methods]
        if isinstance(self.handler, type) and issubclass(self.handler, View):
            self.handler = self.handler.as_view()
        self._pattern = _compile_path(self.path)


def _compile_path(path: str) -> re.Pattern[str]:
    """Convert a path like ``/users/{id}`` to a regex with named groups."""
    # Escape everything except our {param} placeholders
    parts = re.split(r"\{(\w+)\}", path)
    regex = ""
    for i, part in enumerate(parts):
        if i % 2 == 0:
            regex += re.escape(part)
        else:
            regex += rf"(?P<{part}>[^/]+)"
    return re.compile(f"^{regex}$")


class Router:
    """Collects routes and resolves incoming request paths.

    Parameters:
        prefix: Optional path prefix prepended to every route in this router.
    """

    def __init__(self, prefix: str = "") -> None:
        self.prefix: str = prefix.rstrip("/")
        self._routes: list[Route] = []

    # ---- Registration ----------------------------------------------------

    def route(
        self,
        path: str,
        methods: list[str] | None = None,
        name: str | None = None,
        tags: list[str] | None = None,
        summary: str | None = None,
        request_body: type | None = None,
        responses: dict[int, Any] | None = None,
    ) -> Callable[[ViewCallable], ViewCallable]:
        """Decorator to register a function-based view.

        Usage::

            @router.route("/items", methods=["GET"], tags=["Items"], summary="List items")
            async def items(request: RaftRequest) -> RawResponse:
                ...
        """

        def decorator(func: ViewCallable) -> ViewCallable:
            full_path = self.prefix + path
            r = Route(
                path=full_path,
                handler=func,
                methods=methods,
                name=name,
                tags=tags,
                summary=summary,
                request_body=request_body,
                responses=responses,
            )
            self._routes.append(r)
            return func

        return decorator

    def add_route(self, route: Route) -> None:
        """Register a pre-built ``Route`` object."""
        route.path = self.prefix + route.path
        route._pattern = _compile_path(route.path)
        self._routes.append(route)

    def add_routes(self, routes: list[Route]) -> None:
        """Register multiple ``Route`` objects at once (Django-style urlpatterns)."""
        for r in routes:
            self.add_route(r)

    def include_router(self, router: Router) -> None:
        """Merge another router's routes into this one, respecting prefixes."""
        for r in router._routes:
            merged_path = self.prefix + r.path
            new_route = Route(
                path=merged_path,
                handler=r.handler,
                methods=r.methods,
                name=r.name,
                tags=r.tags,
                summary=r.summary,
                request_body=r.request_body,
                responses=r.responses,
            )
            self._routes.append(new_route)

    # ---- Resolution ------------------------------------------------------

    def resolve(self, path: str, method: str) -> tuple[Route, dict[str, str]] | None:
        """Find the first route matching *path* and *method*.

        Returns:
            ``(route, path_params)`` or ``None`` if no match.
        """
        for route in self._routes:
            match = route._pattern.match(path)
            if match is None:
                continue
            if route.methods and method.upper() not in route.methods:
                continue
            return route, match.groupdict()
        return None

    def resolve_path_only(self, path: str) -> Route | None:
        """Check if any route matches the path regardless of method.

        Used to distinguish 404 from 405.
        """
        for route in self._routes:
            if route._pattern.match(path):
                return route
        return None

    @property
    def routes(self) -> list[Route]:
        """All registered routes (read-only)."""
        return list(self._routes)
