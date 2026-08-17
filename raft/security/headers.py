"""
raft.security.headers
~~~~~~~~~~~~~~~~~~~~~

Security headers middleware.

Applies a set of recommended HTTP security headers to every response.
These headers instruct browsers to enable various protections.

Headers applied:
    - ``X-Frame-Options: DENY``  — prevents clickjacking
    - ``X-Content-Type-Options: nosniff`` — prevents MIME sniffing
    - ``Referrer-Policy: strict-origin-when-cross-origin``
    - ``Permissions-Policy`` — restricts powerful APIs
    - ``Strict-Transport-Security`` (HSTS) — enforces HTTPS (prod only)
    - ``Content-Security-Policy`` — basic default-src policy

OpenAPI / Swagger / ReDoc HTML responses set their own ``Content-Security-Policy``
header so CDN scripts (unpkg, jsDelivr) and small inline bootstrappers work;
``setdefault`` here does not override an existing policy.

Production applications should craft a strict CSP tailored to their asset domains.
See ``DEPLOYMENT.md`` for HTTPS, HSTS, and proxy configuration.
"""

from __future__ import annotations

from raft.config.settings import settings
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.base import CallNext


async def security_headers_middleware(
    request: RaftRequest, call_next: CallNext
) -> RawResponse:
    """Attach standard security headers to every response."""
    response = await call_next(request)

    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault(
        "Referrer-Policy", "strict-origin-when-cross-origin"
    )
    response.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), camera=(), microphone=()",
    )
    response.headers.setdefault(
        "Content-Security-Policy", "default-src 'self'"
    )

    # HSTS only when not in debug mode (assumes HTTPS in production).
    if not settings.DEBUG:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload",
        )

    return response
