"""
raft.middleware.xss
~~~~~~~~~~~~~~~~~~~

XSS (Cross-Site Scripting) protection middleware.

This middleware performs two things:

1. **Response header**: Sets ``X-XSS-Protection: 1; mode=block`` (legacy
   but still respected by some browsers) and ``Content-Type-Options: nosniff``.

2. **Input inspection**: Scans query params, path params, selected proxy
    headers, and JSON/form payload values for active-content signatures,
    including encoded variants.

SECURITY NOTE:
     This middleware is defense-in-depth. Keep output escaping and strict CSP
     enabled for complete XSS mitigation.
"""

from __future__ import annotations

from html import unescape
import re
from urllib.parse import unquote_plus

from raft.core.exceptions import HTTPException
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.base import CallNext

# Patterns targeting common active-content injection vectors.
_XSS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<\s*(script|iframe|object|embed|svg|math|link|style)\b", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
    re.compile(r"on(?:error|load|click|mouseover|focus|mouseenter)\s*=", re.IGNORECASE),
    re.compile(r"<\s*/\s*script\s*>", re.IGNORECASE),
]

_BODY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_SCANNED_HEADERS = {
    "x-forwarded-for",
    "x-real-ip",
    "x-client-ip",
    "x-original-url",
    "x-rewrite-url",
}


async def xss_middleware(request: RaftRequest, call_next: CallNext) -> RawResponse:
    """Scan inputs for XSS patterns and set protective response headers."""

    # Check query/path/header values.
    for value in _request_text_candidates(request):
        if _contains_xss(value):
            raise HTTPException(
                status_code=400,
                message="Potentially unsafe content detected in request metadata",
                errors=["XSS pattern detected"],
            )

    # Check payload for state-changing methods.
    if request.method.upper() in _BODY_METHODS:
        content_type = (request.get_header("content-type", "") or "").lower()
        try:
            if "json" in content_type:
                body = await request.json()
                if body is not None and _scan_nested(body):
                    raise HTTPException(
                        status_code=400,
                        message="Potentially unsafe content detected in request body",
                        errors=["XSS pattern detected"],
                    )
            elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                form_data = await request.form()
                if _scan_nested(form_data):
                    raise HTTPException(
                        status_code=400,
                        message="Potentially unsafe content detected in form data",
                        errors=["XSS pattern detected"],
                    )
        except (ValueError, TypeError):
            # Let request parsing/validation middleware raise structured errors.
            pass

    response = await call_next(request)

    # Protective headers
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Content-Type-Options"] = "nosniff"

    return response


def _contains_xss(value: str) -> bool:
    """Return True if *value* matches any XSS pattern."""
    normalized = _normalize(value)
    if not normalized:
        return False
    for pattern in _XSS_PATTERNS:
        if pattern.search(normalized):
            return True
    return False


def _scan_nested(data: object, depth: int = 0) -> bool:
    """Recursively check nested structures for XSS payloads."""
    if depth > 10:
        return False
    if isinstance(data, str):
        return _contains_xss(data)
    if isinstance(data, dict):
        for k, v in data.items():
            if _contains_xss(str(k)) or _scan_nested(v, depth + 1):
                return True
    if isinstance(data, list):
        for item in data:
            if _scan_nested(item, depth + 1):
                return True
    return False


def _request_text_candidates(request: RaftRequest) -> list[str]:
    """Collect metadata values that are high-signal for reflected XSS."""
    values: list[str] = [request.query_string]

    for key, items in request.query_params.items():
        values.append(key)
        values.extend(items)

    for key, value in request.path_params.items():
        values.append(key)
        values.append(value)

    for key, value in request.headers.items():
        if key.lower() in _SCANNED_HEADERS:
            values.append(value)

    return values


def _normalize(value: str) -> str:
    """Decode encoded payload variants so signatures are harder to bypass."""
    result = value
    for _ in range(3):
        decoded = unquote_plus(unescape(result))
        if decoded == result:
            break
        result = decoded
    return result.strip()
