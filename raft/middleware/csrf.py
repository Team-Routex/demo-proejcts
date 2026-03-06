"""
raft.middleware.csrf
~~~~~~~~~~~~~~~~~~~~

CSRF (Cross-Site Request Forgery) protection middleware.

Strategy:
    Uses the Synchronizer Token pattern.  A CSRF token is stored in the
    session and expected in either:
      - An ``X-CSRF-Token`` header, or
      - A ``csrf_token`` form field.

    Safe methods (GET, HEAD, OPTIONS) are exempt.

PROTOTYPE NOTE:
    This is a basic CSRF guard.  For production hardening:
      - Add double-submit cookie support
      - Support per-form tokens with expiry
      - Integrate with template rendering to auto-inject tokens
"""

from __future__ import annotations

import secrets

from raft.core.exceptions import Forbidden
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.base import CallNext

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_CSRF_TOKEN_KEY = "_csrf_token"


async def csrf_middleware(request: RaftRequest, call_next: CallNext) -> RawResponse:
    """Enforce CSRF tokens on state-changing requests."""
    # Ensure a CSRF token exists in the session.
    if _CSRF_TOKEN_KEY not in request.session:
        request.session[_CSRF_TOKEN_KEY] = secrets.token_hex(32)

    if request.method.upper() not in _SAFE_METHODS:
        expected = request.session.get(_CSRF_TOKEN_KEY, "")
        provided = (
            request.get_header("x-csrf-token")
            or (await _get_form_token(request))
        )
        if not secrets.compare_digest(expected, provided or ""):
            raise Forbidden(message="CSRF token missing or invalid")

    response = await call_next(request)
    return response


async def _get_form_token(request: RaftRequest) -> str | None:
    """Try to extract ``csrf_token`` from form data without side effects."""
    content_type = request.get_header("content-type", "")
    if "form" in content_type:
        form_data = await request.form()
        return form_data.get("csrf_token")
    return None
