"""
raft.core.request
~~~~~~~~~~~~~~~~~

ASGI request wrapper.  Provides a clean, typed API over the raw ASGI scope
and body so view functions never touch low-level dictionaries.

Key capabilities:
- IP address extraction (respects ``X-Forwarded-For``)
- User-Agent / browser info
- Query parameter parsing
- Route parameters (path variables)
- Header access
- Cookie access
- JSON body parsing
- Form / multipart file upload handling (via ``python-multipart``)
"""

from __future__ import annotations

import json
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qs

from pydantic import BaseModel


class UploadedFile:
    """Represents a single uploaded file from a multipart request.

    Attributes:
        filename: Original file name from the client.
        content_type: MIME type reported by the client.
        body: Raw bytes of the file content.
    """

    __slots__ = ("filename", "content_type", "body")

    def __init__(self, filename: str, content_type: str, body: bytes) -> None:
        self.filename: str = filename
        self.content_type: str = content_type
        self.body: bytes = body

    @property
    def size(self) -> int:
        """File size in bytes."""
        return len(self.body)

    def save(self, path: str) -> None:
        """Write the uploaded file to *path*."""
        with open(path, "wb") as f:
            f.write(self.body)

    def __repr__(self) -> str:
        return f"<UploadedFile {self.filename!r} ({self.size} bytes)>"


class RaftRequest:
    """Wraps an ASGI HTTP scope + receive callable into a friendly request object.

    Parameters:
        scope: The ASGI connection scope dict.
        receive: The ASGI receive callable.

    All heavy parsing (body, JSON, form data) is lazy — nothing is read until
    the corresponding property / method is awaited.
    """

    def __init__(self, scope: dict[str, Any], receive: Any) -> None:
        self._scope: dict[str, Any] = scope
        self._receive: Any = receive
        self._body: bytes | None = None
        self._json: Any | None = None
        self._form: dict[str, Any] | None = None
        self._files: dict[str, UploadedFile] | None = None
        self.path_params: dict[str, str] = scope.get("path_params", {})
        self.state: dict[str, Any] = {}  # Middleware / view scratch space.
        self.session: dict[str, Any] = {}  # Populated by session middleware.
        self.user: Any = None  # Populated by JWT auth / authentication classes.
        self.auth: Any = None  # Raw credentials (e.g. JWT string) when authenticated.

    # ---- Basic properties ------------------------------------------------

    @property
    def method(self) -> str:
        """HTTP method (GET, POST, …)."""
        return self._scope.get("method", "GET")

    @property
    def path(self) -> str:
        """Request path, e.g. ``/users/42``."""
        return self._scope.get("path", "/")

    @property
    def query_string(self) -> str:
        """Raw query string without leading ``?``."""
        return self._scope.get("query_string", b"").decode("latin-1")

    @property
    def query_params(self) -> dict[str, list[str]]:
        """Parsed query parameters as ``{key: [values]}``."""
        return parse_qs(self.query_string)

    def get_query_param(self, key: str, default: str | None = None) -> str | None:
        """Return first value for *key*, or *default*."""
        values = self.query_params.get(key)
        return values[0] if values else default

    # ---- Headers ---------------------------------------------------------

    @property
    def headers(self) -> dict[str, str]:
        """Request headers as a lowercase-key dict."""
        return {
            k.decode("latin-1"): v.decode("latin-1")
            for k, v in self._scope.get("headers", [])
        }

    def get_header(self, name: str, default: str | None = None) -> str | None:
        """Get a single header value (case-insensitive)."""
        return self.headers.get(name.lower(), default)

    # ---- Cookies ---------------------------------------------------------

    @property
    def cookies(self) -> dict[str, str]:
        """Parsed cookies from the ``Cookie`` header."""
        cookie_header = self.get_header("cookie", "")
        sc: SimpleCookie[str] = SimpleCookie()
        sc.load(cookie_header or "")
        return {k: v.value for k, v in sc.items()}

    def get_cookie(self, name: str, default: str | None = None) -> str | None:
        """Return value for cookie *name*, or *default*."""
        return self.cookies.get(name, default)

    # ---- Client info -----------------------------------------------------

    @property
    def client_ip(self) -> str:
        """Best-effort client IP.  Checks ``X-Forwarded-For`` first."""
        forwarded = self.get_header("x-forwarded-for")
        if forwarded:
            # First entry is the original client.
            return forwarded.split(",")[0].strip()
        client = self._scope.get("client")
        return client[0] if client else "127.0.0.1"

    @property
    def user_agent(self) -> str:
        """Value of the ``User-Agent`` header."""
        return self.get_header("user-agent", "")  # type: ignore[return-value]

    # ---- Body / JSON / Form ----------------------------------------------

    async def body(self) -> bytes:
        """Read and cache the full request body."""
        if self._body is None:
            chunks: list[bytes] = []
            while True:
                message = await self._receive()
                chunk = message.get("body", b"")
                if chunk:
                    chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            self._body = b"".join(chunks)
        return self._body

    async def json(self) -> Any:
        """Parse the body as JSON and return the result."""
        if self._json is None:
            raw = await self.body()
            self._json = json.loads(raw) if raw else None
        return self._json

    async def form(self) -> dict[str, Any]:
        """Parse URL-encoded or multipart form data using ``python-multipart``."""
        if self._form is not None:
            return self._form

        content_type = self.get_header("content-type", "")
        raw = await self.body()

        if "application/x-www-form-urlencoded" in content_type:
            parsed = parse_qs(raw.decode("utf-8"))
            self._form = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        elif "multipart/form-data" in content_type:
            self._form, self._files = _parse_multipart(raw, content_type)
        else:
            self._form = {}

        return self._form

    async def files(self) -> dict[str, UploadedFile]:
        """Return uploaded files from a multipart request."""
        if self._files is None:
            await self.form()  # triggers multipart parsing
        return self._files or {}

    # ---- Validation helper -----------------------------------------------

    async def validate(self, model: type[BaseModel]) -> BaseModel:
        """Validate the JSON body against a Pydantic *model*.

        Returns:
            A validated model instance.

        Raises:
            pydantic.ValidationError on invalid data (caught by the
            framework's exception handler and turned into a 422 response).
        """
        data = await self.json()
        return model.model_validate(data)


# ---------------------------------------------------------------------------
# Multipart parsing (python-multipart)
# ---------------------------------------------------------------------------

def _parse_multipart(
    raw: bytes, content_type: str
) -> tuple[dict[str, Any], dict[str, UploadedFile]]:
    """Parse multipart/form-data with python-multipart."""
    from python_multipart.multipart import FormParser, parse_options_header

    fields: dict[str, Any] = {}
    files: dict[str, UploadedFile] = {}

    _, params = parse_options_header(content_type.encode("latin-1"))
    boundary = params.get(b"boundary")
    if boundary is None:
        return fields, files

    def on_field(field: Any) -> None:
        name = field.field_name.decode("utf-8", errors="replace")
        value = field.value.decode("utf-8", errors="replace")
        if name in fields:
            existing = fields[name]
            if isinstance(existing, list):
                existing.append(value)
            else:
                fields[name] = [existing, value]
        else:
            fields[name] = value

    def on_file(file: Any) -> None:
        name = file.field_name.decode("utf-8", errors="replace")
        filename = (file.file_name or b"upload").decode("utf-8", errors="replace")
        file.file_object.seek(0)
        body = file.file_object.read()
        ct = "application/octet-stream"
        files[name] = UploadedFile(
            filename=filename,
            content_type=ct,
            body=body,
        )

    parser = FormParser(
        "multipart/form-data",
        on_field,
        on_file,
        boundary=boundary,
    )
    parser.write(raw)
    parser.close()
    return fields, files
