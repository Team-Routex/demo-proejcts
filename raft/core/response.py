"""
raft.core.response
~~~~~~~~~~~~~~~~~~

Structured JSON response helpers.

Every JSON response follows a unified envelope::

    {
        "status": true,
        "message": "...",
        "data": {...}
    }

The ``errors`` key is **only** included on **failed** responses (``status: false``)
when there is at least one non-empty error string.

Primary API::

    return Response.success(data={"id": 1})
    return Response.error(message="Invalid", errors=["name: required"], http_status=400)

Subclass ``Response`` to add project-specific helpers::

    class APIResponse(Response):
        @classmethod
        def paginated(cls, items, total, page):
            return cls.success(data={"items": items, "total": total, "page": page})

For non-JSON responses (HTML, redirects, files), use ``RawResponse``.
"""

from __future__ import annotations

import json
from http.cookies import SimpleCookie
from typing import Any


class RawResponse:
    """Low-level ASGI HTTP response."""

    def __init__(
        self,
        body: bytes = b"",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        content_type: str = "text/plain",
    ) -> None:
        self.body: bytes = body
        self.status_code: int = status_code
        self.headers: dict[str, str] = headers or {}
        self.content_type: str = content_type
        self._cookies: SimpleCookie[str] = SimpleCookie()

    def set_cookie(
        self,
        name: str,
        value: str,
        max_age: int | None = None,
        path: str = "/",
        httponly: bool = True,
        secure: bool = False,
        samesite: str = "Lax",
        domain: str | None = None,
    ) -> None:
        """Set a cookie on this response."""
        self._cookies[name] = value
        morsel = self._cookies[name]
        morsel["path"] = path
        morsel["httponly"] = httponly
        morsel["samesite"] = samesite
        if max_age is not None:
            morsel["max-age"] = str(max_age)
        if secure:
            morsel["secure"] = True  # type: ignore[assignment]
        if domain:
            morsel["domain"] = domain

    def delete_cookie(
        self,
        name: str,
        path: str = "/",
        domain: str | None = None,
    ) -> None:
        """Expire a cookie immediately."""
        self.set_cookie(name, "", max_age=0, path=path, domain=domain)

    async def send(self, send: Any) -> None:
        """Serialize this response over the ASGI *send* callable."""
        raw_headers: list[tuple[bytes, bytes]] = [
            (b"content-type", self.content_type.encode()),
        ]
        for k, v in self.headers.items():
            raw_headers.append((k.lower().encode(), v.encode()))

        for morsel in self._cookies.values():
            raw_headers.append((b"set-cookie", morsel.OutputString().encode()))

        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": raw_headers,
            }
        )
        await send({"type": "http.response.body", "body": self.body})


class Response:
    """Factory for structured JSON responses.

    Use :meth:`success` and :meth:`error` as the primary API. Named helpers
    (``created``, ``not_found``, etc.) delegate to those methods. Subclass
    to add custom response shapes for your application.
    """

    @classmethod
    def build(
        cls,
        *,
        status: bool,
        message: str,
        data: dict[str, Any] | list[Any] | None = None,
        errors: list[str] | None = None,
        http_status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> RawResponse:
        """Low-level builder — override in subclasses for custom envelopes."""
        payload: dict[str, Any] = {
            "status": status,
            "message": message,
            "data": data,
        }
        if not status:
            filtered = [str(e).strip() for e in (errors or []) if str(e).strip()]
            if filtered:
                payload["errors"] = filtered

        body = json.dumps(payload, default=str).encode("utf-8")
        return RawResponse(
            body=body,
            status_code=http_status,
            headers=headers or {},
            content_type="application/json",
        )

    # ── Primary API ───────────────────────────────────────────────────────

    @classmethod
    def success(
        cls,
        message: str = "Success",
        data: dict[str, Any] | list[Any] | None = None,
        *,
        http_status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> RawResponse:
        """Successful JSON response (default 200)."""
        return cls.build(
            status=True,
            message=message,
            data=data,
            http_status=http_status,
            headers=headers,
        )

    @classmethod
    def error(
        cls,
        message: str = "Error",
        errors: list[str] | None = None,
        *,
        http_status: int = 400,
        data: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RawResponse:
        """Failed JSON response (default 400)."""
        return cls.build(
            status=False,
            message=message,
            data=data,
            errors=errors,
            http_status=http_status,
            headers=headers,
        )

    # ── Success shortcuts ─────────────────────────────────────────────────

    @classmethod
    def created(
        cls,
        message: str = "Created",
        data: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RawResponse:
        """201 Created."""
        return cls.success(message, data, http_status=201, headers=headers)

    @classmethod
    def no_content(cls, message: str = "No Content") -> RawResponse:
        """204 No Content."""
        return cls.success(message, None, http_status=204)

    # ── Error shortcuts ───────────────────────────────────────────────────

    @classmethod
    def bad_request(
        cls,
        message: str = "Bad Request",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """400 Bad Request."""
        return cls.error(message, errors, http_status=400)

    @classmethod
    def unauthorized(
        cls,
        message: str = "Unauthorized",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """401 Unauthorized."""
        return cls.error(message, errors, http_status=401)

    @classmethod
    def forbidden(
        cls,
        message: str = "Forbidden",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """403 Forbidden."""
        return cls.error(message, errors, http_status=403)

    @classmethod
    def not_found(
        cls,
        message: str = "Not Found",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """404 Not Found."""
        return cls.error(message, errors, http_status=404)

    @classmethod
    def method_not_allowed(
        cls,
        message: str = "Method Not Allowed",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """405 Method Not Allowed."""
        return cls.error(message, errors, http_status=405)

    @classmethod
    def unprocessable(
        cls,
        message: str = "Validation Error",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """422 Unprocessable Entity."""
        return cls.error(message, errors, http_status=422)

    @classmethod
    def internal_error(
        cls,
        message: str = "Internal Server Error",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """500 Internal Server Error."""
        return cls.error(message, errors, http_status=500)

    @classmethod
    def custom(
        cls,
        status: bool,
        message: str,
        data: dict[str, Any] | list[Any] | None = None,
        errors: list[str] | None = None,
        http_status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> RawResponse:
        """Build a response with explicit success/failure and HTTP status."""
        return cls.build(
            status=status,
            message=message,
            data=data,
            errors=errors,
            http_status=http_status,
            headers=headers,
        )


# Deprecated alias — use Response
RaftResponse = Response
