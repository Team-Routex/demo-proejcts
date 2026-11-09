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
        _set_cors_headers(response, origin, request)
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

    response = await call_next(request)

    if allowed:
        _set_cors_headers(response, origin, request)

    return response


def _is_origin_allowed(origin: str) -> bool:
    """Check origin against the configured allow-list."""
    if not origin:
        return False
    if "*" in settings.CORS_ALLOWED_ORIGINS:
        return True
    return origin in settings.CORS_ALLOWED_ORIGINS


def _set_cors_headers(response: RawResponse, origin: str, request: RaftRequest | None = None) -> None:
    """Apply CORS headers to *response*."""
    if "*" in settings.CORS_ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = "*"
    else:
        response.headers["Access-Control-Allow-Origin"] = origin or "*"

    existing_vary = response.headers.get("Vary")
    if existing_vary:
        vary_tokens = [v.strip().lower() for v in existing_vary.split(",")]
        if "origin" not in vary_tokens:
            response.headers["Vary"] = f"{existing_vary}, Origin"
    else:
        response.headers["Vary"] = "Origin"

    response.headers["Access-Control-Allow-Methods"] = ", ".join(
        settings.CORS_ALLOW_METHODS
    )
    
    req_headers = ""
    if request:
        req_headers = request.get_header("access-control-request-headers", "")
        if request.get_header("access-control-request-private-network") == "true":
            response.headers["Access-Control-Allow-Private-Network"] = "true"

    if req_headers:
        response.headers["Access-Control-Allow-Headers"] = req_headers
    else:
        response.headers["Access-Control-Allow-Headers"] = ", ".join(
            settings.CORS_ALLOW_HEADERS
        )
