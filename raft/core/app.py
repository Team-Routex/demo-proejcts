"""
raft.core.app
~~~~~~~~~~~~~

The main ``Raft`` ASGI application class.

``Raft`` ties together routing, middleware, sessions, error handling,
and response serialization into a single ASGI-compatible application.

Minimal usage::

    from raft import Raft, RaftResponse

    app = Raft()

    @app.route("/", methods=["GET"])
    async def index(request):
        return RaftResponse.ok(message="Welcome to Raft!")

Running::

    # Development (hot reload)
    raft runserver --reload

    # Production
    uvicorn app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
import traceback
from pathlib import Path
from typing import Any, Callable, Awaitable

from pydantic import ValidationError as PydanticValidationError

from raft.config.settings import settings
from raft.core.exceptions import HTTPException, ValidationError
from raft.core.request import RaftRequest
from raft.core.response import RaftResponse, RawResponse
from raft.core.router import Route, Router, ViewCallable
from raft.middleware.base import MiddlewareFunc, MiddlewarePipeline
from raft.middleware.cors import cors_middleware
from raft.middleware.csrf import csrf_middleware
from raft.middleware.sqli import sqli_middleware
from raft.middleware.xss import xss_middleware
from raft.security.headers import security_headers_middleware
from raft.session.backend import session_middleware_factory
from raft.tasks.scheduler import TASK_OPTIONS_ATTR, TaskScheduler
from raft.websocket.connection import RaftWebSocket
from raft.websocket.manager import WebSocketManager
from raft.websocket.router import WebSocketRoute, WebSocketRouter, WebSocketHandler

logger = logging.getLogger("raft")

LifecycleHandler = Callable[[], Awaitable[None] | None]


class Raft:
    """The Raft ASGI application.

    Parameters:
        debug: Override the DEBUG setting for this app instance.
        enable_sessions: Attach session middleware (default True).
        enable_cors: Attach CORS middleware (default True).
        enable_csrf: Attach CSRF middleware (default False — enable for
                     HTML-form-serving apps).
        enable_security_headers: Attach security-headers middleware (default True).
        enable_xss: Attach XSS scanning middleware (default True).
        enable_sqli: Attach SQLi scanning middleware (default True).
        auto_discover_routes: Load ``router`` from each module under the routes
            directory (default from ``RAFT_AUTO_DISCOVER_ROUTES``).
        auto_discover_serializers: Load ``Serializer`` subclasses from the
            serializers package (default from ``RAFT_AUTO_DISCOVER_SERIALIZERS``).
    """

    def __init__(
        self,
        debug: bool | None = None,
        auto_discover_middleware: bool | None = None,
        auto_discover_tasks: bool | None = None,
        enable_sessions: bool = True,
        enable_cors: bool = True,
        enable_csrf: bool = False,
        enable_security_headers: bool = True,
        enable_xss: bool = True,
        enable_sqli: bool = True,
        auto_discover_routes: bool | None = None,
        auto_discover_serializers: bool | None = None,
    ) -> None:
        self.debug: bool = debug if debug is not None else settings.DEBUG
        self.router: Router = Router()
        self.websocket_router: WebSocketRouter = WebSocketRouter()
        self.websocket_manager: WebSocketManager = WebSocketManager()
        self.scheduler: TaskScheduler = TaskScheduler()
        self._startup_handlers: list[LifecycleHandler] = [self.scheduler.start]
        self._shutdown_handlers: list[LifecycleHandler] = [self.scheduler.stop]

        # Middleware pipeline — order matters.
        self._pipeline: MiddlewarePipeline = MiddlewarePipeline()
        self._chain: Callable[[RaftRequest], Awaitable[RawResponse]] | None = None

        # Register built-in middleware in the correct order.
        # Outermost (first to run) → innermost (closest to view):
        if enable_security_headers:
            self._pipeline.add(security_headers_middleware)
        if enable_cors:
            self._pipeline.add(cors_middleware)
        if enable_sessions:
            self._pipeline.add(session_middleware_factory())
        if enable_csrf:
            self._pipeline.add(csrf_middleware)
        if enable_xss:
            self._pipeline.add(xss_middleware)
        if enable_sqli:
            self._pipeline.add(sqli_middleware)

        should_discover_tasks = (
            settings.AUTO_DISCOVER_TASKS
            if auto_discover_tasks is None
            else auto_discover_tasks
        )
        if should_discover_tasks:
            self.autodiscover_tasks()

        should_discover = (
            settings.AUTO_DISCOVER_MIDDLEWARE
            if auto_discover_middleware is None
            else auto_discover_middleware
        )
        if should_discover:
            self.autodiscover_middlewares()

        should_discover_routes = (
            settings.AUTO_DISCOVER_ROUTES
            if auto_discover_routes is None
            else auto_discover_routes
        )
        if should_discover_routes:
            self.autodiscover_routes()

        should_discover_serializers = (
            settings.AUTO_DISCOVER_SERIALIZERS
            if auto_discover_serializers is None
            else auto_discover_serializers
        )
        if should_discover_serializers:
            self.autodiscover_serializers()

    # ---- Route registration shortcuts ------------------------------------

    def route(
        self,
        path: str,
        methods: list[str] | None = None,
        name: str | None = None,
        tags: list[str] | None = None,
        summary: str | None = None,
        request_body: type | None = None,
        responses: dict[int, Any] | None = None,
        request_serializer: type | None = None,
        response_serializer: type | None = None,
    ) -> Callable[[ViewCallable], ViewCallable]:
        """Decorator shortcut for ``self.router.route(...)``."""
        self._chain = None  # invalidate cached chain
        return self.router.route(
            path,
            methods=methods,
            name=name,
            tags=tags,
            summary=summary,
            request_body=request_body,
            responses=responses,
            request_serializer=request_serializer,
            response_serializer=response_serializer,
        )

    def add_route(self, route: Route) -> None:
        """Register a Route object directly."""
        self._chain = None
        self.router.add_route(route)

    def add_routes(self, routes: list[Route]) -> None:
        """Register multiple ``Route`` objects at once (URL-conf list style)."""
        self._chain = None
        self.router.add_routes(routes)

    def include_router(self, router: Router) -> None:
        """Merge an external router's routes."""
        self._chain = None
        self.router.include_router(router)

    def autodiscover_routes(
        self,
        directory: str | Path | None = None,
    ) -> int:
        """Load ``Router`` instances from a project ``routes`` directory.

        Discovery rules:
            - Scans ``<cwd>/<directory>/*.py`` excluding ``__init__.py`` and
              private modules (``_*``).
            - If a module defines ``ROUTERS`` (list/tuple of ``Router``), each
              is merged.
            - Otherwise, if the module defines ``router`` as a ``Router``,
              it is merged.

        Environment:
            ``RAFT_AUTO_DISCOVER_ROUTES``, ``RAFT_ROUTES_DIR`` (see settings).
        """
        routes_dir_name = directory or settings.ROUTES_MODULE_DIR
        base_dir = settings.BASE_DIR if isinstance(settings.BASE_DIR, Path) else Path.cwd()
        routes_dir = base_dir / str(routes_dir_name)

        if not routes_dir.exists() or not routes_dir.is_dir():
            return 0

        loaded = 0
        for file_path in sorted(routes_dir.glob("*.py")):
            if file_path.name.startswith("_") or file_path.name == "__init__.py":
                continue

            module = self._load_module_from_path(
                file_path, namespace="routes", log_label="routes"
            )
            if module is None:
                continue

            for subrouter in self._extract_routers(module):
                self.include_router(subrouter)
                loaded += 1
                logger.info("New router detected: %s (%s)", subrouter.prefix or "/", file_path.name)

        return loaded

    @staticmethod
    def _extract_routers(module: Any) -> list[Router]:
        explicit = getattr(module, "ROUTERS", None)
        if isinstance(explicit, (list, tuple)):
            routers = [r for r in explicit if isinstance(r, Router)]
            if routers:
                return routers

        router = getattr(module, "router", None)
        if isinstance(router, Router):
            return [router]

        return []

    def autodiscover_serializers(
        self,
        directory: str | Path | None = None,
    ) -> int:
        """Register ``Serializer`` subclasses from a project ``serializers`` folder.

        Scans ``*.py`` (skips ``__init__.py`` and ``_*``). Each defined subclass
        of :class:`raft.serialization.base.Serializer` is registered for OpenAPI
        components and introspection.

        Environment: ``RAFT_AUTO_DISCOVER_SERIALIZERS``, ``RAFT_SERIALIZERS_DIR``.
        """
        from raft.serialization.base import Serializer
        from raft.serialization.registry import register_serializer

        serializers_dir_name = directory or settings.SERIALIZERS_MODULE_DIR
        base_dir = settings.BASE_DIR if isinstance(settings.BASE_DIR, Path) else Path.cwd()
        ser_dir = base_dir / str(serializers_dir_name)

        if not ser_dir.exists() or not ser_dir.is_dir():
            return 0

        loaded = 0
        for file_path in sorted(ser_dir.glob("*.py")):
            if file_path.name.startswith("_") or file_path.name == "__init__.py":
                continue

            module = self._load_module_from_path(
                file_path, namespace="serializers", log_label="serializers"
            )
            if module is None:
                continue

            mod_name = module.__name__
            for _name, obj in inspect.getmembers(module):
                if not isinstance(obj, type):
                    continue
                if getattr(obj, "__module__", None) != mod_name:
                    continue
                if not issubclass(obj, Serializer) or obj is Serializer:
                    continue
                register_serializer(obj)
                loaded += 1
                logger.info("Serializer registered: %s (%s)", obj.__name__, file_path.name)

        return loaded

    def websocket(
        self,
        path: str,
        *,
        name: str | None = None,
    ) -> Callable[[WebSocketHandler], WebSocketHandler]:
        """Decorator shortcut for ``self.websocket_router.websocket(...)``."""
        return self.websocket_router.websocket(path, name=name)

    def add_websocket(self, route: WebSocketRoute) -> None:
        """Register a websocket route object directly."""
        self.websocket_router.add_route(route)

    # ---- Middleware -------------------------------------------------------

    def add_middleware(self, middleware: MiddlewareFunc) -> None:
        """Add a custom middleware to the pipeline."""
        self._chain = None
        self._pipeline.add(middleware)

    def autodiscover_middlewares(
        self,
        directory: str | Path | None = None,
    ) -> int:
        """Auto-load middleware callables from a project middleware directory.

        Discovery rules:
            - Scans ``<cwd>/<directory>/*.py`` excluding private modules.
            - Registers async callables named ``*_middleware``.
            - Also supports explicit module-level ``MIDDLEWARE`` list/tuple.
        """
        middleware_dir_name = directory or settings.MIDDLEWARE_MODULE_DIR
        base_dir = settings.BASE_DIR if isinstance(settings.BASE_DIR, Path) else Path.cwd()
        middleware_dir = base_dir / str(middleware_dir_name)

        if not middleware_dir.exists() or not middleware_dir.is_dir():
            return 0

        loaded = 0
        for file_path in sorted(middleware_dir.glob("*.py")):
            if file_path.name.startswith("_"):
                continue

            module = self._load_module_from_path(
                file_path, namespace="middleware", log_label="middleware"
            )
            if module is None:
                continue

            for name, middleware in self._extract_middlewares(module):
                if not self._is_valid_middleware(middleware):
                    continue
                self.add_middleware(middleware)
                loaded += 1
                logger.info("New middleware detected: %s (%s)", name, file_path.name)

        return loaded

    @staticmethod
    def _load_module_from_path(
        file_path: Path,
        namespace: str = "middleware",
        *,
        log_label: str = "middleware",
    ) -> Any | None:
        module_name = f"raft_user_{namespace}_{file_path.stem}_{abs(hash(str(file_path)))}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:
            logger.exception("Failed to import %s module: %s", log_label, file_path)
            return None
        return module

    @staticmethod
    def _extract_middlewares(module: Any) -> list[tuple[str, Any]]:
        explicit = getattr(module, "MIDDLEWARE", None)
        extracted: list[tuple[str, Any]] = []

        if isinstance(explicit, (list, tuple)):
            for idx, candidate in enumerate(explicit):
                name = getattr(candidate, "__name__", f"middleware_{idx}")
                extracted.append((name, candidate))
            return extracted

        for name, candidate in inspect.getmembers(module):
            if not inspect.iscoroutinefunction(candidate):
                continue
            if name.endswith("_middleware"):
                extracted.append((name, candidate))

        return extracted

    @staticmethod
    def _is_valid_middleware(candidate: Any) -> bool:
        if not inspect.iscoroutinefunction(candidate):
            return False
        try:
            signature = inspect.signature(candidate)
        except (TypeError, ValueError):
            return False
        # Expected: (request, call_next)
        return len(signature.parameters) == 2

    def on_startup(self, handler: LifecycleHandler) -> LifecycleHandler:
        """Register a startup lifecycle handler."""
        self._startup_handlers.append(handler)
        return handler

    def on_shutdown(self, handler: LifecycleHandler) -> LifecycleHandler:
        """Register a shutdown lifecycle handler."""
        self._shutdown_handlers.append(handler)
        return handler

    def task(
        self,
        *,
        every: float,
        repeat: bool = True,
        name: str | None = None,
        run_immediately: bool = False,
    ) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
        """Decorator for periodic background tasks.

        Usage::

            @app.task(every=60, repeat=True, run_immediately=True)
            async def refresh_cache():
                ...
        """
        return self.scheduler.task(
            every=every,
            repeat=repeat,
            name=name,
            run_immediately=run_immediately,
        )

    def add_task(
        self,
        func: Callable[[], Any],
        *,
        every: float,
        repeat: bool = True,
        name: str | None = None,
        run_immediately: bool = False,
    ) -> Callable[[], Any]:
        """Programmatically register a periodic background task."""
        return self.scheduler.add_task(
            func,
            every=every,
            repeat=repeat,
            name=name,
            run_immediately=run_immediately,
        )

    def autodiscover_tasks(
        self,
        directory: str | Path | None = None,
    ) -> int:
        """Auto-load periodic tasks from a project tasks directory."""
        tasks_dir_name = directory or settings.TASKS_MODULE_DIR
        base_dir = settings.BASE_DIR if isinstance(settings.BASE_DIR, Path) else Path.cwd()
        tasks_dir = base_dir / str(tasks_dir_name)

        if not tasks_dir.exists() or not tasks_dir.is_dir():
            return 0

        loaded = 0
        seen_ids: set[int] = set()
        for file_path in sorted(tasks_dir.glob("*.py")):
            if file_path.name.startswith("_"):
                continue

            module = self._load_module_from_path(
                file_path, namespace="task", log_label="tasks"
            )
            if module is None:
                continue

            for name, (func, options) in self._extract_tasks(module):
                if id(func) in seen_ids:
                    continue
                seen_ids.add(id(func))

                self.add_task(
                    func,
                    every=float(options["every"]),
                    repeat=bool(options.get("repeat", True)),
                    name=options.get("name") or name,
                    run_immediately=bool(options.get("run_immediately", False)),
                )
                loaded += 1
                logger.info("New task detected: %s (%s)", name, file_path.name)

        return loaded

    @staticmethod
    def _extract_tasks(module: Any) -> list[tuple[str, tuple[Callable[[], Any], dict[str, Any]]]]:
        extracted: list[tuple[str, tuple[Callable[[], Any], dict[str, Any]]]] = []
        explicit = getattr(module, "TASKS", None)

        if isinstance(explicit, (list, tuple)):
            for idx, candidate in enumerate(explicit):
                normalized = Raft._normalize_task_candidate(candidate, idx)
                if normalized is not None:
                    extracted.append(normalized)

        for name, candidate in inspect.getmembers(module):
            options = getattr(candidate, TASK_OPTIONS_ATTR, None)
            if callable(candidate) and isinstance(options, dict):
                extracted.append((name, (candidate, options)))

        return extracted

    @staticmethod
    def _normalize_task_candidate(
        candidate: Any,
        index: int,
    ) -> tuple[str, tuple[Callable[[], Any], dict[str, Any]]] | None:
        if callable(candidate):
            options = getattr(candidate, TASK_OPTIONS_ATTR, None)
            if isinstance(options, dict):
                name = getattr(candidate, "__name__", f"task_{index}")
                return name, (candidate, options)
            return None

        if isinstance(candidate, dict):
            func = candidate.get("func")
            every = candidate.get("every")
            if not callable(func) or every is None:
                return None
            options = {
                "every": float(every),
                "repeat": bool(candidate.get("repeat", True)),
                "name": candidate.get("name"),
                "run_immediately": bool(candidate.get("run_immediately", False)),
            }
            name = options.get("name") or getattr(func, "__name__", f"task_{index}")
            return str(name), (func, options)

        return None

    async def _run_lifecycle_handlers(
        self,
        handlers: list[LifecycleHandler],
    ) -> None:
        """Execute lifecycle handlers in registration order."""
        for handler in handlers:
            result = handler()
            if inspect.isawaitable(result):
                await result

    # ---- ASGI interface ---------------------------------------------------

    async def __call__(
        self, scope: dict[str, Any], receive: Any, send: Any
    ) -> None:
        """ASGI entry point."""
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    try:
                        await self._run_lifecycle_handlers(self._startup_handlers)
                        await send({"type": "lifespan.startup.complete"})
                    except Exception as exc:
                        await send(
                            {
                                "type": "lifespan.startup.failed",
                                "message": str(exc),
                            }
                        )
                elif message["type"] == "lifespan.shutdown":
                    try:
                        await self._run_lifecycle_handlers(self._shutdown_handlers)
                        await send({"type": "lifespan.shutdown.complete"})
                    except Exception as exc:
                        await send(
                            {
                                "type": "lifespan.shutdown.failed",
                                "message": str(exc),
                            }
                        )
                    return
            return

        if scope["type"] == "websocket":
            await self._dispatch_websocket(scope, receive, send)
            return

        if scope["type"] != "http":
            return

        request = RaftRequest(scope, receive)

        try:
            # Build the middleware chain once (lazy, cached).
            if self._chain is None:
                self._chain = self._pipeline.build_chain(self._dispatch)

            response = await self._chain(request)
        except HTTPException as exc:
            response = RaftResponse._build(
                status=False,
                message=exc.message,
                errors=exc.errors,
                http_status=exc.status_code,
            )
        except PydanticValidationError as exc:
            errors = [
                f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
                for e in exc.errors()
            ]
            response = RaftResponse.unprocessable(
                message="Validation Error", errors=errors
            )
        except Exception as exc:
            logger.exception("Unhandled exception in Raft application")
            msg = str(exc) if self.debug else "Internal Server Error"
            tb = traceback.format_exc() if self.debug else None
            errors = [tb] if tb else []
            response = RaftResponse.internal_error(message=msg, errors=errors)

        await response.send(send)

    # ---- Internal dispatch ------------------------------------------------

    async def _dispatch(self, request: RaftRequest) -> RawResponse:
        """Resolve the route and call the view handler."""
        result = self.router.resolve(request.path, request.method)

        if result is None:
            # Distinguish 404 from 405.
            if self.router.resolve_path_only(request.path):
                return RaftResponse.method_not_allowed(
                    message=f"Method {request.method} not allowed for {request.path}"
                )
            return RaftResponse.not_found(
                message=f"No route matches {request.path}"
            )

        route, path_params = result
        request.path_params = path_params
        return await route.handler(request)

    async def _dispatch_websocket(
        self,
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        """Resolve and dispatch websocket handlers with a simple room manager."""
        websocket = RaftWebSocket(
            scope=scope,
            receive=receive,
            send=send,
            manager=self.websocket_manager,
        )

        resolved = self.websocket_router.resolve(websocket.path)
        if resolved is None:
            await websocket.close(code=4404, reason="WebSocket route not found")
            return

        route, path_params = resolved
        websocket.path_params = path_params
        self.websocket_manager.connect(websocket)

        try:
            # Easy default: handlers can send/receive immediately.
            await websocket.accept()
            await route.handler(websocket)
        except ConnectionError:
            # Client disconnected while handler was waiting for messages.
            pass
        except Exception as exc:
            logger.exception("Unhandled exception in websocket handler")
            reason = str(exc)[:120] if self.debug else "Internal Server Error"
            await websocket.close(code=1011, reason=reason)
        finally:
            self.websocket_manager.disconnect(websocket)
            if not websocket.is_closed:
                await websocket.close()
