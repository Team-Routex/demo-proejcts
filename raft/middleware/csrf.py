"""
raft.middleware.csrf
~~~~~~~~~~~~~~~~~~~~

CSRF (Cross-Site Request Forgery) protection middleware.

Strategy:
    Uses the Synchronizer Token pattern.  A CSRF token is stored in the
        session and expected in either:
      - An ``X-CSRF-Token`` header, or
            - An ``X-XSRF-Token`` header,
            - A ``csrf_token`` cookie, or
      - A ``csrf_token`` form field.

        For state-changing methods, Origin/Referer host is also validated against
        Host when these headers are present.

    Safe methods (GET, HEAD, OPTIONS) are exempt.
"""

from __future__ import annotations

import hmac
import secrets
from urllib.parse import urlparse

from raft.core.exceptions import Forbidden
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.base import CallNext

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
_CSRF_TOKEN_KEY = "_csrf_token"
_CSRF_COOKIE_NAME = "csrf_token"


async def csrf_middleware(request: RaftRequest, call_next: CallNext) -> RawResponse:
    """Enforce CSRF tokens on state-changing requests."""
    # Ensure a CSRF token exists in the session.
    if _CSRF_TOKEN_KEY not in request.session:
        request.session[_CSRF_TOKEN_KEY] = secrets.token_hex(32)

    if request.method.upper() not in _SAFE_METHODS:
        expected = str(request.session.get(_CSRF_TOKEN_KEY, ""))
        provided = await _get_request_csrf_token(request)

        if not _is_same_origin_request(request):
            raise Forbidden(message="Cross-origin CSRF validation failed")

        if not expected or not provided or not hmac.compare_digest(expected, provided):
            raise Forbidden(message="CSRF token missing or invalid")

    response = await call_next(request)
    token = str(request.session.get(_CSRF_TOKEN_KEY, ""))
    # Expose token for clients that need to bootstrap AJAX requests.
    response.headers.setdefault("X-CSRF-Token", token)
    response.set_cookie(
        _CSRF_COOKIE_NAME,
        token,
        path="/",
        httponly=False,
        samesite="Lax",
        secure=False,
    )
    return response


async def _get_request_csrf_token(request: RaftRequest) -> str | None:
    """Extract CSRF token from header, cookie, or form payload."""
    header_token = request.get_header("x-csrf-token") or request.get_header("x-xsrf-token")
    if header_token:
        return header_token

    cookie_token = request.get_cookie(_CSRF_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    # Fallback for form submissions.
    content_type = request.get_header("content-type", "")
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form_data = await request.form()
        return form_data.get("csrf_token")
    return None


def _is_same_origin_request(request: RaftRequest) -> bool:
    """Validate Origin/Referer host against Host to reduce CSRF abuse."""
    host = request.get_header("host", "") or ""
    if not host:
        return True

    origin = request.get_header("origin")
    if origin:
        parsed_origin = urlparse(origin)
        origin_host = parsed_origin.netloc
        if origin_host and origin_host.lower() != host.lower():
            return False

    referer = request.get_header("referer")
    if referer:
        parsed_referer = urlparse(referer)
        referer_host = parsed_referer.netloc
        if referer_host and referer_host.lower() != host.lower():
            return False

    return True
