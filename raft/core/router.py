"""
raft.core.router
~~~~~~~~~~~~~~~~

Uniform hybrid routing for Raft — method decorators, Django-style route
tables, and project-wide route discovery — in one module.

1. **Method decorators**::

       router = Router()

       @router.get("/users")
       async def list_users(request):
           ...

       @router.get(
           "/me",
           authentication_classes=[JWTAuthentication],
           permission_classes=[IsAuthenticated],
       )
       async def me(request):
           ...

2. **Django-style route table**::

       from raft import route, include

       routes = [
           route("/users/", list_users, methods=["GET"]),
           route(
               "/me/",
               me,
               methods=["GET"],
               authentication_classes=[JWTAuthentication],
               permission_classes=[IsAuthenticated],
           ),
           route("/api/", include([
               route("/items/", list_items, methods=["GET"]),
           ])),
       ]
       app.add_routes(routes)

3. **Autodiscovery** — ``iter_route_module_files`` finds modules that export
   ``routes`` / ``router`` / ``ROUTERS`` anywhere under the project root.

``@router.route(..., methods=[...])`` remains for multi-method handlers.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.core.views import View


# Type alias for a view callable (FBV).
ViewCallable = Callable[[RaftRequest], Awaitable[RawResponse]]


# ── Compiled Route ────────────────────────────────────────────────────────────


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


def path_resolution_candidates(path: str) -> list[str]:
    """Paths to try when matching, in order.

    The request path is always tried first. If that fails, a single trailing-slash
    variant is tried so ``/users/1/`` matches a route registered as ``/users/{id}``,
    and ``/users/1`` matches ``/users/{id}/`` when that is how the route was
    declared.
    """
    candidates: list[str] = []
    seen: set[str] = set()

    def push(p: str) -> None:
        if p in seen:
            return
        seen.add(p)
        candidates.append(p)

    push(path)
    if len(path) > 1 and path.endswith("/"):
        push(path[:-1])
    elif path not in ("", "/") and not path.endswith("/"):
        push(path + "/")
    return candidates


def _compile_path(path: str) -> re.Pattern[str]:
    """Convert a path like ``/users/{id}`` to a regex with named groups."""
    parts = re.split(r"\{(\w+)\}", path)
    regex = ""
    for i, part in enumerate(parts):
        if i % 2 == 0:
            regex += re.escape(part)
        else:
            regex += rf"(?P<{part}>[^/]+)"
    return re.compile(f"^{regex}$")


# ── Django-style route table helpers ──────────────────────────────────────────


@dataclass
class URLPattern:
    """One concrete path → view mapping produced by ``route()``."""

    path: str
    view: ViewCallable | type[View]
    name: str | None = None
    methods: list[str] | None = None
    tags: list[str] | None = None
    summary: str | None = None
    request_body: type | None = None
    responses: dict[int, Any] | None = None
    authentication_classes: list[Any] | None = None
    permission_classes: list[Any] | None = None

    def to_route(self, *, prefix: str = "") -> Route:
        """Compile this pattern into a ``Route`` under *prefix*."""
        from raft.auth.decorators import apply_view_auth

        full_path = _join_path(prefix, self.path)
        handler: Any = self.view
        # CBV class attributes already run in View.dispatch; route-level
        # kwargs wrap the callable (also covers FBVs).
        if self.authentication_classes or self.permission_classes:
            if isinstance(handler, type) and issubclass(handler, View):
                handler = handler.as_view()
            handler = apply_view_auth(
                handler,
                authentication_classes=self.authentication_classes,
                permission_classes=self.permission_classes,
            )
        return Route(
            path=full_path,
            handler=handler,
            methods=self.methods,
            name=self.name,
            tags=self.tags,
            summary=self.summary,
            request_body=self.request_body,
            responses=self.responses,
        )


@dataclass
class URLResolver:
    """Nested route entries returned by ``include()``."""

    patterns: list[URLPattern | URLInclude | Route] = field(default_factory=list)


@dataclass
class URLInclude:
    """A ``route(prefix, include(...))`` entry — mount nested routes under *prefix*."""

    prefix: str
    patterns: list[URLPattern | URLInclude | Route]


URLConfEntry = URLPattern | URLInclude | Route | URLResolver


def _join_path(prefix: str, path: str) -> str:
    """Join a prefix and path into a single URL path."""
    prefix = (prefix or "").rstrip("/")
    path = path or ""
    if path and not path.startswith("/"):
        path = "/" + path
    if not prefix:
        return path or "/"
    if not path or path == "/":
        return prefix or "/"
    return prefix + path


def route(
    path: str,
    view: ViewCallable | type[View] | URLResolver | list[URLConfEntry] | tuple[URLConfEntry, ...],
    *,
    name: str | None = None,
    methods: list[str] | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
    request_body: type | None = None,
    responses: dict[int, Any] | None = None,
    authentication_classes: list[Any] | None = None,
    permission_classes: list[Any] | None = None,
) -> URLPattern | URLInclude:
    """Declare a route entry for a central ``routes`` table.

    *view* may be:
        - an async view callable
        - a ``View`` subclass (CBV)
        - an ``include(...)`` / ``URLResolver`` for nesting
        - a raw list/tuple of entries (treated as ``include``)

    Optional ``authentication_classes`` / ``permission_classes``
    wrap function views (CBVs usually set these as class attributes instead).
    """
    if isinstance(view, URLResolver):
        return URLInclude(prefix=path, patterns=list(view.patterns))
    if isinstance(view, (list, tuple)):
        return URLInclude(prefix=path, patterns=list(view))

    return URLPattern(
        path=path,
        view=view,
        name=name,
        methods=methods,
        tags=tags,
        summary=summary,
        request_body=request_body,
        responses=responses,
        authentication_classes=authentication_classes,
        permission_classes=permission_classes,
    )


def include(
    arg: Sequence[URLConfEntry] | URLResolver,
) -> URLResolver:
    """Include a list of route entries (Django-style nesting).

    Usage::

        route("/api/", include([
            route("/users/", list_users, methods=["GET"]),
        ]))
    """
    if isinstance(arg, URLResolver):
        return arg
    return URLResolver(patterns=list(arg))


def flatten_routes(
    patterns: Sequence[URLConfEntry],
    *,
    prefix: str = "",
) -> list[Route]:
    """Expand ``route`` / ``include`` / ``Route`` entries into flat ``Route`` objects."""
    out: list[Route] = []
    for entry in patterns:
        if isinstance(entry, URLResolver):
            out.extend(flatten_routes(entry.patterns, prefix=prefix))
        elif isinstance(entry, URLInclude):
            nested_prefix = _join_path(prefix, entry.prefix)
            out.extend(flatten_routes(entry.patterns, prefix=nested_prefix))
        elif isinstance(entry, URLPattern):
            out.append(entry.to_route(prefix=prefix))
        elif isinstance(entry, Route):
            if prefix:
                out.append(
                    Route(
                        path=_join_path(prefix, entry.path),
                        handler=entry.handler,
                        methods=entry.methods,
                        name=entry.name,
                        tags=entry.tags,
                        summary=entry.summary,
                        request_body=entry.request_body,
                        request_serializer=entry.request_serializer,
                        response_serializer=entry.response_serializer,
                        responses=entry.responses,
                    )
                )
            else:
                out.append(entry)
        else:
            raise TypeError(
                f"Invalid routes entry: {entry!r}. "
                "Expected route(), include(), or Route."
            )
    return out


# ── Project-wide discovery ────────────────────────────────────────────────────

_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".idea",
        ".vscode",
        "node_modules",
        "dist",
        "build",
        "site-packages",
        "tests",
        "test",
    }
)

_SKIP_FILES: frozenset[str] = frozenset(
    {
        "app.py",
        "main.py",
        "conftest.py",
        "setup.py",
        "manage.py",
    }
)

_CANDIDATE_RE = re.compile(
    r"""(?x)
    \broutes\s*=
    | \bROUTERS\s*=
    | \brouter\s*=
    | \bRouter\s*\(
    | @router\.
    | from\s+raft\s+import\s+.*\broute\b
    | from\s+raft\.core\.router\s+import\s+.*\broute\b
    """
)


def iter_route_module_files(
    root: Path,
    *,
    only_under: Path | None = None,
) -> list[Path]:
    """Return project ``.py`` files that look like they define routes.

    Parameters:
        root: Project base directory (typically ``settings.BASE_DIR``).
        only_under: If set, limit the walk to this subdirectory.
    """
    root = root.resolve()
    start = only_under.resolve() if only_under is not None else root
    if not start.exists() or not start.is_dir():
        return []

    found: list[Path] = []
    for path in sorted(start.rglob("*.py")):
        if not path.is_file():
            continue
        if not _is_discoverable_file(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not _CANDIDATE_RE.search(text):
            continue
        found.append(path)
    return found


def _is_discoverable_file(path: Path, root: Path) -> bool:
    name = path.name
    if name.startswith("_") or name == "__init__.py":
        return False
    if name in _SKIP_FILES:
        return False
    if name.startswith("test_") or name.endswith("_test.py"):
        return False

    try:
        rel = path.resolve().relative_to(root)
    except ValueError:
        return False

    parts = rel.parts
    if any(part in _SKIP_DIRS for part in parts[:-1]):
        return False
    if any(part.endswith(".egg-info") for part in parts):
        return False

    if parts and parts[0] == "raft" and (root / "raft" / "core" / "app.py").is_file():
        return False
    if parts and parts[0] in {"raftsql", "RaftSQL"}:
        return False

    return True


# ── Router ────────────────────────────────────────────────────────────────────


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
        authentication_classes: list[Any] | None = None,
        permission_classes: list[Any] | None = None,
    ) -> Callable[[ViewCallable], ViewCallable]:
        """Low-level decorator for one or more HTTP methods.

        Prefer ``@router.get`` / ``@router.post`` / etc. for single-method
        endpoints. Use this when one handler must accept multiple methods.

        Pass ``authentication_classes`` / ``permission_classes`` for view auth
        protection on the decorated function view.
        """

        def decorator(func: ViewCallable) -> ViewCallable:
            from raft.auth.decorators import apply_view_auth

            full_path = self.prefix + path
            handler = apply_view_auth(
                func,
                authentication_classes=authentication_classes,
                permission_classes=permission_classes,
            )
            r = Route(
                path=full_path,
                handler=handler,  # type: ignore[arg-type]
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

    def get(self, path: str, **kwargs: Any) -> Callable[[ViewCallable], ViewCallable]:
        """Register a GET handler: ``@router.get("/items", permission_classes=[...])``."""
        return self.route(path, methods=["GET"], **kwargs)

    def post(self, path: str, **kwargs: Any) -> Callable[[ViewCallable], ViewCallable]:
        """Register a POST handler: ``@router.post("/items", permission_classes=[...])``."""
        return self.route(path, methods=["POST"], **kwargs)

    def put(self, path: str, **kwargs: Any) -> Callable[[ViewCallable], ViewCallable]:
        """Register a PUT handler: ``@router.put("/items/{id}")``."""
        return self.route(path, methods=["PUT"], **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Callable[[ViewCallable], ViewCallable]:
        """Register a PATCH handler: ``@router.patch("/items/{id}")``."""
        return self.route(path, methods=["PATCH"], **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Callable[[ViewCallable], ViewCallable]:
        """Register a DELETE handler: ``@router.delete("/items/{id}")``."""
        return self.route(path, methods=["DELETE"], **kwargs)

    def head(self, path: str, **kwargs: Any) -> Callable[[ViewCallable], ViewCallable]:
        """Register a HEAD handler: ``@router.head("/items")``."""
        return self.route(path, methods=["HEAD"], **kwargs)

    def options(self, path: str, **kwargs: Any) -> Callable[[ViewCallable], ViewCallable]:
        """Register an OPTIONS handler: ``@router.options("/items")``."""
        return self.route(path, methods=["OPTIONS"], **kwargs)

    def add_route(self, route_obj: Route) -> None:
        """Register a pre-built ``Route`` object."""
        route_obj.path = self.prefix + route_obj.path
        route_obj._pattern = _compile_path(route_obj.path)
        self._routes.append(route_obj)

    def add_routes(self, routes: Sequence[Any]) -> None:
        """Register ``Route`` objects or a Django-style ``routes`` table.

        Accepts ``route()`` / ``include()`` entries and/or ``Route`` instances.
        """
        for compiled in flatten_routes(routes):
            self.add_route(compiled)

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
        for candidate in path_resolution_candidates(path):
            for route_obj in self._routes:
                match = route_obj._pattern.match(candidate)
                if match is None:
                    continue
                if route_obj.methods and method.upper() not in route_obj.methods:
                    continue
                return route_obj, match.groupdict()
        return None

    def resolve_path_only(self, path: str) -> Route | None:
        """Check if any route matches the path regardless of method.

        Used to distinguish 404 from 405.
        """
        for candidate in path_resolution_candidates(path):
            for route_obj in self._routes:
                if route_obj._pattern.match(candidate):
                    return route_obj
        return None

    @property
    def routes(self) -> list[Route]:
        """All registered routes (read-only)."""
        return list(self._routes)
