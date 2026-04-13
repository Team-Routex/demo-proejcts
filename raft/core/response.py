"""
raft.core.response
~~~~~~~~~~~~~~~~~~

Structured JSON response helpers.

Every Raft response follows a unified envelope::

    {
        "status": true,
        "message": "...",
        "data": {...}
    }

The ``errors`` key is **only** included on **failed** responses (``status: false``)
when there is at least one non-empty error string. It is never sent on success
(``status: true``), even if a caller mistakenly passes error strings.

``RaftResponse`` provides class methods for common HTTP status codes so
view code stays concise:

    return RaftResponse.ok(data={"id": 1})
    return RaftResponse.created(data=user_dict)
    return RaftResponse.bad_request(errors=["Name is required"])

For non-JSON responses (HTML, redirects, files), use ``RawResponse``.
"""

from __future__ import annotations

import json
from http.cookies import SimpleCookie
from typing import Any


class RawResponse:
    """Low-level ASGI HTTP response.

    Parameters:
        body: Response body bytes.
        status_code: HTTP status code.
        headers: Extra headers as ``{name: value}``.
        content_type: MIME content type.
    """

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

    def delete_cookie(self, name: str, path: str = "/") -> None:
        """Expire a cookie immediately."""
        self.set_cookie(name, "", max_age=0, path=path)

    # ---- ASGI send -------------------------------------------------------

    async def send(self, send: Any) -> None:
        """Serialize this response over the ASGI *send* callable."""
        raw_headers: list[tuple[bytes, bytes]] = [
            (b"content-type", self.content_type.encode()),
        ]
        for k, v in self.headers.items():
            raw_headers.append((k.lower().encode(), v.encode()))

        # Append Set-Cookie headers
        for morsel in self._cookies.values():
            raw_headers.append(
                (b"set-cookie", morsel.OutputString().encode())
            )

        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": raw_headers,
            }
        )
        await send({"type": "http.response.body", "body": self.body})


class RaftResponse:
    """Factory for structured JSON responses.

    Every method returns a ``RawResponse`` whose body follows the unified
    Raft envelope format.
    """

    @staticmethod
    def _build(
        status: bool,
        message: str,
        data: dict[str, Any] | list[Any] | None = None,
        errors: list[str] | None = None,
        http_status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> RawResponse:
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

    # -- Success helpers ---------------------------------------------------

    @classmethod
    def ok(
        cls,
        message: str = "Success",
        data: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RawResponse:
        """200 OK."""
        return cls._build(
            status=True, message=message, data=data, http_status=200, headers=headers
        )

    @classmethod
    def created(
        cls,
        message: str = "Created",
        data: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RawResponse:
        """201 Created."""
        return cls._build(
            status=True, message=message, data=data, http_status=201, headers=headers
        )

    @classmethod
    def no_content(cls, message: str = "No Content") -> RawResponse:
        """204 No Content."""
        return cls._build(status=True, message=message, http_status=204)

    # -- Error helpers -----------------------------------------------------

    @classmethod
    def bad_request(
        cls,
        message: str = "Bad Request",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """400 Bad Request."""
        return cls._build(status=False, message=message, errors=errors, http_status=400)

    @classmethod
    def unauthorized(
        cls,
        message: str = "Unauthorized",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """401 Unauthorized."""
        return cls._build(status=False, message=message, errors=errors, http_status=401)

    @classmethod
    def forbidden(
        cls,
        message: str = "Forbidden",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """403 Forbidden."""
        return cls._build(status=False, message=message, errors=errors, http_status=403)

    @classmethod
    def not_found(
        cls,
        message: str = "Not Found",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """404 Not Found."""
        return cls._build(status=False, message=message, errors=errors, http_status=404)

    @classmethod
    def method_not_allowed(
        cls,
        message: str = "Method Not Allowed",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """405 Method Not Allowed."""
        return cls._build(status=False, message=message, errors=errors, http_status=405)

    @classmethod
    def unprocessable(
        cls,
        message: str = "Validation Error",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """422 Unprocessable Entity (validation errors)."""
        return cls._build(status=False, message=message, errors=errors, http_status=422)

    @classmethod
    def internal_error(
        cls,
        message: str = "Internal Server Error",
        errors: list[str] | None = None,
    ) -> RawResponse:
        """500 Internal Server Error."""
        return cls._build(status=False, message=message, errors=errors, http_status=500)

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
        """Build a response with a fully custom status code."""
        return cls._build(
            status=status,
            message=message,
            data=data,
            errors=errors,
            http_status=http_status,
            headers=headers,
        )
