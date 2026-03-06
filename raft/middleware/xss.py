"""
raft.middleware.xss
~~~~~~~~~~~~~~~~~~~

XSS (Cross-Site Scripting) protection middleware.

This middleware performs two things:

1. **Response header**: Sets ``X-XSS-Protection: 1; mode=block`` (legacy
   but still respected by some browsers) and ``Content-Type-Options: nosniff``.

2. **Input sanitization (prototype)**: Scans incoming JSON body keys/values
   and query parameters for obvious ``<script>`` patterns and rejects
   requests that contain them.

PROTOTYPE NOTE:
    Real XSS protection requires output encoding at the template layer and
    a strict Content-Security-Policy.  This middleware is a *belt-and-suspenders*
    check — it does NOT replace proper output escaping.  For production:
      - Use a real HTML sanitizer (e.g. ``bleach`` or ``nh3``)
      - Implement CSP headers
      - Encode output contextually (HTML, JS, URL, CSS)
"""

from __future__ import annotations

import re

from raft.core.exceptions import HTTPException
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.base import CallNext

# Simple patterns that suggest script injection.  Not exhaustive.
_XSS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),  # onerror=, onclick=, …
]


async def xss_middleware(request: RaftRequest, call_next: CallNext) -> RawResponse:
    """Scan inputs for XSS patterns and set protective response headers."""

    # Check query string
    if _contains_xss(request.query_string):
        raise HTTPException(
            status_code=400,
            message="Potentially unsafe content detected in query parameters",
            errors=["XSS pattern detected"],
        )

    # Check JSON body for unsafe methods
    if request.method.upper() in {"POST", "PUT", "PATCH"}:
        content_type = request.get_header("content-type", "")
        if "json" in content_type:
            try:
                body = await request.json()
                if body and _scan_dict(body):
                    raise HTTPException(
                        status_code=400,
                        message="Potentially unsafe content detected in request body",
                        errors=["XSS pattern detected"],
                    )
            except (ValueError, TypeError):
                pass  # Not valid JSON — other validation will catch it.

    response = await call_next(request)

    # Protective headers
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Content-Type-Options"] = "nosniff"

    return response


def _contains_xss(value: str) -> bool:
    """Return True if *value* matches any XSS pattern."""
    for pattern in _XSS_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _scan_dict(data: object, depth: int = 0) -> bool:
    """Recursively check dict/list values for XSS patterns.

    Limits recursion to 10 levels to avoid abuse.
    """
    if depth > 10:
        return False
    if isinstance(data, str):
        return _contains_xss(data)
    if isinstance(data, dict):
        for k, v in data.items():
            if _contains_xss(str(k)) or _scan_dict(v, depth + 1):
                return True
    if isinstance(data, list):
        for item in data:
            if _scan_dict(item, depth + 1):
                return True
    return False
