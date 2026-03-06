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

logger = logging.getLogger("raft")


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

    # ---- Middleware -------------------------------------------------------

    def add_middleware(self, middleware: MiddlewareFunc) -> None:
        """Add a custom middleware to the pipeline."""
        self._chain = None
        self._pipeline.add(middleware)

    # ---- ASGI interface ---------------------------------------------------

    async def __call__(
        self, scope: dict[str, Any], receive: Any, send: Any
    ) -> None:
        """ASGI entry point."""
        if scope["type"] == "lifespan":
            # Accept lifespan events but do nothing for now.
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
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
