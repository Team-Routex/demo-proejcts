"""
raft.core.exceptions
~~~~~~~~~~~~~~~~~~~~

Structured HTTP exceptions.

Raising an ``HTTPException`` inside a view or middleware is the idiomatic way
to abort request processing.  The Raft app catches these and converts them
into a structured JSON response automatically.

Example::

    from raft.core.exceptions import HTTPException
    raise HTTPException(status_code=403, message="Not allowed")

Validation errors raised by Pydantic are caught separately and
returned as 422 responses.
"""

from __future__ import annotations

from typing import Any


class HTTPException(Exception):
    """An HTTP error that the framework renders as a structured JSON response.

    Parameters:
        status_code: HTTP status code (e.g. 400, 404, 500).
        message: Human-readable explanation.
        errors: Optional list of specific error strings.
    """

    def __init__(
        self,
        status_code: int = 400,
        message: str = "Bad Request",
        errors: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code: int = status_code
        self.message: str = message
        self.errors: list[str] = errors or []


class ValidationError(HTTPException):
    """A 422 validation error with structured detail.

    Typically created from Pydantic ``ValidationError`` instances by the
    framework, but can be raised manually.
    """

    def __init__(
        self,
        message: str = "Validation Error",
        errors: list[str] | None = None,
        detail: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(status_code=422, message=message, errors=errors)
        self.detail: list[dict[str, Any]] = detail or []


class NotFound(HTTPException):
    """Convenience: 404 Not Found."""

    def __init__(self, message: str = "Not Found") -> None:
        super().__init__(status_code=404, message=message)


class MethodNotAllowed(HTTPException):
    """Convenience: 405 Method Not Allowed."""

    def __init__(self, message: str = "Method Not Allowed") -> None:
        super().__init__(status_code=405, message=message)


class Forbidden(HTTPException):
    """Convenience: 403 Forbidden."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(status_code=403, message=message)


class Unauthorized(HTTPException):
    """Convenience: 401 Unauthorized."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(status_code=401, message=message)
