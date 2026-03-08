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

import inspect
import logging
import traceback
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
from raft.tasks.scheduler import TaskScheduler
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
    """

    def __init__(
        self,
        debug: bool | None = None,
        enable_sessions: bool = True,
        enable_cors: bool = True,
        enable_csrf: bool = False,
        enable_security_headers: bool = True,
        enable_xss: bool = True,
        enable_sqli: bool = True,
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
        )

    def add_route(self, route: Route) -> None:
        """Register a Route object directly."""
        self._chain = None
        self.router.add_route(route)

    def add_routes(self, routes: list[Route]) -> None:
        """Register multiple Route objects (Django urlpatterns style)."""
        self._chain = None
        self.router.add_routes(routes)

    def include_router(self, router: Router) -> None:
        """Merge an external router's routes."""
        self._chain = None
        self.router.include_router(router)

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
