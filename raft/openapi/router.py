"""
raft.openapi.router
~~~~~~~~~~~~~~~~~~~

Mounts ``/openapi.json``, ``/docs`` (Swagger UI), and ``/redoc`` onto a
Raft ``Router`` so they can be included into any ``Raft`` app.

The OpenAPI schema is **generated lazily** on the first request to
``/openapi.json`` — this ensures all application routes have been registered
before the spec is built.

Usage::

    from raft import Raft
    from raft.openapi.router import OpenAPIRouter

    app = Raft()

    # ... register your routes ...

    openapi = OpenAPIRouter(
        app,
        title="My API",
        version="1.0.0",
        description="Built with Raft Framework",
    )
    app.include_router(openapi.router)

Endpoints:
    GET /openapi.json  — raw OpenAPI 3.0.3 JSON spec
    GET /docs          — Swagger UI
    GET /redoc         — ReDoc
"""

from __future__ import annotations

import base64
import binascii
import hmac
import json
from typing import Any

from raft.config.settings import settings
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.core.router import Router
from raft.openapi.schema import build_openapi_schema
from raft.openapi.ui import redoc_html, swagger_ui_html

# Relaxed CSP for HTML doc pages only. Default ``default-src 'self'`` from
# ``security_headers_middleware`` blocks CDN scripts + inline bootstrappers,
# which leaves Swagger UI / ReDoc blank.
_DOCS_PAGE_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://unpkg.com; "
    "connect-src 'self'; "
    "img-src 'self' data: blob: https:; "
    "font-src 'self' https://unpkg.com data:;"
)


class OpenAPIRouter:
    """Generates and serves OpenAPI docs for a Raft application.

    Parameters:
        app_or_router: The ``Raft`` app instance (or a bare ``Router``).
                       Passed by reference so that routes registered after
                       this object is created are still included in the spec.
        title: API title displayed in Swagger UI / ReDoc.
        version: API version string.
        description: Optional Markdown description for the API overview.
        docs_url: URL path for Swagger UI (default ``/docs``).
        redoc_url: URL path for ReDoc (default ``/redoc``).
        openapi_url: URL path for the raw JSON spec (default ``/openapi.json``).
        servers: Optional list of OpenAPI server objects.
        docs_visibility: ``public`` (default) or ``private``.
        docs_password: Password for private docs. If omitted, reads
                       ``RAFT_OPENAPI_DOCS_PASSWORD`` from environment.
    """

    def __init__(
        self,
        app_or_router: Any,
        *,
        title: str = "Raft API",
        version: str = "0.1.0",
        description: str = "",
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
        openapi_url: str = "/openapi.json",
        servers: list[dict[str, str]] | None = None,
        docs_visibility: str | None = None,
        docs_password: str | None = None,
    ) -> None:
        self._source = app_or_router
        self.title = title
        self.version = version
        self.description = description
        self.docs_url = docs_url
        self.redoc_url = redoc_url
        self.openapi_url = openapi_url
        self.servers = servers
        configured_visibility = docs_visibility or settings.OPENAPI_DOCS_VISIBILITY
        normalized_visibility = configured_visibility.strip().lower()
        self.docs_visibility = (
            "private" if normalized_visibility == "private" else "public"
        )
        configured_password = (
            settings.OPENAPI_DOCS_PASSWORD if docs_password is None else docs_password
        )
        self.docs_password = configured_password.strip()

        # Paths to exclude from the generated spec (the doc routes themselves)
        self._exclude_paths: set[str] = {docs_url, redoc_url, openapi_url}

        # Lazily populated on first GET /openapi.json — cleared via invalidate()
        self._cached_schema: dict[str, Any] | None = None

        # The Router that exposes the 3 doc endpoints
        self.router: Router = Router()
        self._mount()

    # ---- Public helpers --------------------------------------------------

    def invalidate_cache(self) -> None:
        """Force the schema to be rebuilt on the next request.

        Call this if you dynamically add routes after startup.
        """
        self._cached_schema = None

    # ---- Internal --------------------------------------------------------

    def _get_source_router(self) -> Router:
        """Resolve the Router from either a Raft app or a bare Router."""
        if hasattr(self._source, "router"):
            return self._source.router  # type: ignore[return-value]
        return self._source  # type: ignore[return-value]

    def _generate_schema(self) -> dict[str, Any]:
        return build_openapi_schema(
            self._get_source_router(),
            title=self.title,
            version=self.version,
            description=self.description,
            servers=self.servers,
            exclude_paths=self._exclude_paths,
        )

    def _is_docs_authorized(self, request: RaftRequest) -> bool:
        """Return True when docs are public or valid password was supplied."""
        if self.docs_visibility != "private":
            return True
        if not self.docs_password:
            return False

        authorization = request.get_header("authorization", "") or ""
        parts = authorization.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "basic":
            return False

        try:
            decoded = base64.b64decode(parts[1]).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            return False

        if ":" not in decoded:
            return False

        _, provided_password = decoded.split(":", 1)
        return hmac.compare_digest(provided_password, self.docs_password)

    def _unauthorized_response(self) -> RawResponse:
        """Return HTTP Basic auth challenge response for private docs."""
        return RawResponse(
            body=b"Unauthorized: API docs password required",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Raft API Docs"'},
            content_type="text/plain; charset=utf-8",
        )

    def _mount(self) -> None:
        """Register the three doc endpoints on self.router."""

        # Capture locals so closures don't re-read mutated variables
        openapi_url = self.openapi_url
        docs_url = self.docs_url
        redoc_url = self.redoc_url
        title = self.title
        this = self  # reference to the OpenAPIRouter instance

        # --- /openapi.json ------------------------------------------------
        @this.router.route(openapi_url, methods=["GET"])
        async def openapi_json(request: RaftRequest) -> RawResponse:
            """Serve the raw OpenAPI 3.0.3 JSON specification."""
            if not this._is_docs_authorized(request):
                return this._unauthorized_response()
            if this._cached_schema is None:
                this._cached_schema = this._generate_schema()
            return RawResponse(
                body=json.dumps(this._cached_schema, indent=2, default=str).encode(),
                status_code=200,
                content_type="application/json",
            )

        # --- /docs (Swagger UI) -------------------------------------------
        @this.router.route(docs_url, methods=["GET"])
        async def swagger_ui(request: RaftRequest) -> RawResponse:
            """Serve the Swagger UI interactive documentation."""
            if not this._is_docs_authorized(request):
                return this._unauthorized_response()
            html = swagger_ui_html(openapi_url=openapi_url, title=title)
            return RawResponse(
                body=html.encode("utf-8"),
                status_code=200,
                content_type="text/html; charset=utf-8",
                headers={"Content-Security-Policy": _DOCS_PAGE_CSP},
            )

        # --- /redoc -------------------------------------------------------
        @this.router.route(redoc_url, methods=["GET"])
        async def redoc(request: RaftRequest) -> RawResponse:
            """Serve the ReDoc documentation page."""
            if not this._is_docs_authorized(request):
                return this._unauthorized_response()
            html = redoc_html(openapi_url=openapi_url, title=title)
            return RawResponse(
                body=html.encode("utf-8"),
                status_code=200,
                content_type="text/html; charset=utf-8",
                headers={"Content-Security-Policy": _DOCS_PAGE_CSP},
            )
