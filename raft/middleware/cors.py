"""
raft.middleware.cors
~~~~~~~~~~~~~~~~~~~~

CORS (Cross-Origin Resource Sharing) middleware.

Handles preflight ``OPTIONS`` requests and sets the appropriate
``Access-Control-*`` headers on every response.

Configuration is read from ``raft.config.settings``.

PROTOTYPE NOTE:
    This middleware covers the most common CORS use-cases.  For advanced
    scenarios (per-route origins, credentials, exposed headers), extend
    this or replace it with a dedicated CORS library.
"""

from __future__ import annotations

from raft.config.settings import settings
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.base import CallNext


async def cors_middleware(request: RaftRequest, call_next: CallNext) -> RawResponse:
    """Add CORS headers and handle preflight requests."""
    origin = request.get_header("origin", "")

    # Determine if this origin is allowed
    allowed = _is_origin_allowed(origin)

    # Preflight
    if request.method == "OPTIONS" and allowed:
        response = RawResponse(status_code=204)
        _set_cors_headers(response, origin)
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

    response = await call_next(request)

    if allowed:
        _set_cors_headers(response, origin)

    return response


def _is_origin_allowed(origin: str) -> bool:
    """Check origin against the configured allow-list."""
    if not origin:
        return False
    if "*" in settings.CORS_ALLOWED_ORIGINS:
        return True
    return origin in settings.CORS_ALLOWED_ORIGINS


def _set_cors_headers(response: RawResponse, origin: str) -> None:
    """Apply CORS headers to *response*."""
    allow_origin = origin if origin else "*"
    response.headers["Access-Control-Allow-Origin"] = allow_origin
    response.headers["Access-Control-Allow-Methods"] = ", ".join(
        settings.CORS_ALLOW_METHODS
    )
    response.headers["Access-Control-Allow-Headers"] = ", ".join(
        settings.CORS_ALLOW_HEADERS
    )
