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

import json
from typing import Any

from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.core.router import Router
from raft.openapi.schema import build_openapi_schema
from raft.openapi.ui import redoc_html, swagger_ui_html


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
    ) -> None:
        self._source = app_or_router
        self.title = title
        self.version = version
        self.description = description
        self.docs_url = docs_url
        self.redoc_url = redoc_url
        self.openapi_url = openapi_url
        self.servers = servers

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
            html = swagger_ui_html(openapi_url=openapi_url, title=title)
            return RawResponse(
                body=html.encode("utf-8"),
                status_code=200,
                content_type="text/html; charset=utf-8",
            )

        # --- /redoc -------------------------------------------------------
        @this.router.route(redoc_url, methods=["GET"])
        async def redoc(request: RaftRequest) -> RawResponse:
            """Serve the ReDoc documentation page."""
            html = redoc_html(openapi_url=openapi_url, title=title)
            return RawResponse(
                body=html.encode("utf-8"),
                status_code=200,
                content_type="text/html; charset=utf-8",
            )
