"""
raft.openapi.router
~~~~~~~~~~~~~~~~~~~

Mounts ``/openapi.json``, ``/docs`` (Swagger UI), and ``/redoc`` onto a
Raft ``Router``.

Docs access (``.env``)::

    # Turn off entirely in production (404)
    RAFT_OPENAPI_DOCS_ENABLED=false

    # Or protect with HTTP Basic (username + password)
    RAFT_OPENAPI_DOCS_ENABLED=true
    RAFT_OPENAPI_DOCS_USERNAME=docs
    RAFT_OPENAPI_DOCS_PASSWORD=secret

    # Legacy alias: visibility=disabled also turns docs off
    # RAFT_OPENAPI_DOCS_VISIBILITY=disabled
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
        app_or_router: The ``Raft`` app (or a bare ``Router``).
        title / version / description: Spec metadata.
        docs_url / redoc_url / openapi_url: Endpoint paths.
        servers: Optional OpenAPI server objects.
        docs_enabled: Override ``RAFT_OPENAPI_DOCS_ENABLED``.
        docs_visibility: ``public``, ``private``, or ``disabled``.
        docs_username / docs_password: HTTP Basic credentials when protecting docs.
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
        docs_enabled: bool | None = None,
        docs_visibility: str | None = None,
        docs_username: str | None = None,
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

        visibility = (
            docs_visibility
            if docs_visibility is not None
            else settings.OPENAPI_DOCS_VISIBILITY
        ).strip().lower()
        if visibility not in {"public", "private", "disabled"}:
            visibility = "public"
        self.docs_visibility = visibility

        enabled_flag = (
            settings.OPENAPI_DOCS_ENABLED if docs_enabled is None else docs_enabled
        )
        self.docs_enabled = bool(enabled_flag) and visibility != "disabled"

        username = (
            settings.OPENAPI_DOCS_USERNAME if docs_username is None else docs_username
        )
        password = (
            settings.OPENAPI_DOCS_PASSWORD if docs_password is None else docs_password
        )
        self.docs_username = (username or "").strip()
        self.docs_password = (password or "").strip()

        # Protect when credentials are set, or visibility is private
        if self.docs_visibility == "private":
            self._auth_required = True
            if not self.docs_username:
                self.docs_username = "admin"
        else:
            self._auth_required = bool(self.docs_username and self.docs_password)

        self._exclude_paths: set[str] = {docs_url, redoc_url, openapi_url}
        self._cached_schema: dict[str, Any] | None = None
        self.router: Router = Router()
        self._mount()

    def invalidate_cache(self) -> None:
        """Force the schema to be rebuilt on the next request."""
        self._cached_schema = None

    def _get_source_router(self) -> Router:
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

    def _disabled_response(self) -> RawResponse:
        return RawResponse(
            body=b"Not Found",
            status_code=404,
            content_type="text/plain; charset=utf-8",
        )

    def _unauthorized_response(self) -> RawResponse:
        return RawResponse(
            body=b"Unauthorized: API docs credentials required",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Raft API Docs"'},
            content_type="text/plain; charset=utf-8",
        )

    def _is_docs_authorized(self, request: RaftRequest) -> bool:
        if not self._auth_required:
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

        provided_user, provided_password = decoded.split(":", 1)
        try:
            user_ok = hmac.compare_digest(
                provided_user.encode("utf-8"),
                self.docs_username.encode("utf-8"),
            )
            pass_ok = hmac.compare_digest(
                provided_password.encode("utf-8"),
                self.docs_password.encode("utf-8"),
            )
        except (TypeError, ValueError):
            return False
        return user_ok and pass_ok

    def _mount(self) -> None:
        openapi_url = self.openapi_url
        docs_url = self.docs_url
        redoc_url = self.redoc_url
        title = self.title
        this = self

        @this.router.get(openapi_url)
        async def openapi_json(request: RaftRequest) -> RawResponse:
            if not this.docs_enabled:
                return this._disabled_response()
            if not this._is_docs_authorized(request):
                return this._unauthorized_response()
            if this._cached_schema is None:
                this._cached_schema = this._generate_schema()
            return RawResponse(
                body=json.dumps(this._cached_schema, indent=2, default=str).encode(),
                status_code=200,
                content_type="application/json",
            )

        @this.router.get(docs_url)
        async def swagger_ui(request: RaftRequest) -> RawResponse:
            if not this.docs_enabled:
                return this._disabled_response()
            if not this._is_docs_authorized(request):
                return this._unauthorized_response()
            html = swagger_ui_html(openapi_url=openapi_url, title=title)
            return RawResponse(
                body=html.encode("utf-8"),
                status_code=200,
                content_type="text/html; charset=utf-8",
                headers={"Content-Security-Policy": _DOCS_PAGE_CSP},
            )

        @this.router.get(redoc_url)
        async def redoc(request: RaftRequest) -> RawResponse:
            if not this.docs_enabled:
                return this._disabled_response()
            if not this._is_docs_authorized(request):
                return this._unauthorized_response()
            html = redoc_html(openapi_url=openapi_url, title=title)
            return RawResponse(
                body=html.encode("utf-8"),
                status_code=200,
                content_type="text/html; charset=utf-8",
                headers={"Content-Security-Policy": _DOCS_PAGE_CSP},
            )
