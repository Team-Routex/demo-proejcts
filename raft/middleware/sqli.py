"""
raft.middleware.sqli
~~~~~~~~~~~~~~~~~~~~

SQL Injection avoidance middleware.

Scans query/path params, selected headers, and JSON/form payload values for
common SQL injection signatures and rejects suspicious requests with a 400.

SECURITY NOTE:
    This is defense-in-depth. The primary SQLi defense remains parameterized
    queries / ORM query builders.
"""

from __future__ import annotations

from html import unescape
import re
from urllib.parse import unquote_plus

from raft.core.exceptions import HTTPException
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.base import CallNext

# Common SQL injection indicators (case-insensitive).
_SQLI_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bunion\s+(all\s+)?select\b", re.IGNORECASE),
    re.compile(r"\b(or|and)\b\s+\d+\s*=\s*\d+", re.IGNORECASE),
    re.compile(r"'\s*or\s*'1'\s*=\s*'1", re.IGNORECASE),
    re.compile(r"\bexec(ute)?\b\s+(xp_|sp_)", re.IGNORECASE),
    re.compile(r"(--|#|/\*)", re.IGNORECASE),
    re.compile(r";\s*(drop|alter|truncate|insert|delete|update)\b", re.IGNORECASE),
]

_BODY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_SCANNED_HEADERS = {
    "x-forwarded-for",
    "x-real-ip",
    "x-client-ip",
    "x-original-url",
    "x-rewrite-url",
}


async def sqli_middleware(request: RaftRequest, call_next: CallNext) -> RawResponse:
    """Reject requests containing obvious SQL injection patterns."""

    for value in _request_text_candidates(request):
        if _contains_sqli(value):
            raise HTTPException(
                status_code=400,
                message="Potentially unsafe SQL content detected in request metadata",
                errors=["SQL injection pattern detected"],
            )

    if request.method.upper() in _BODY_METHODS:
        content_type = (request.get_header("content-type", "") or "").lower()
        try:
            if "json" in content_type:
                body = await request.json()
                if body is not None and _scan_nested(body):
                    raise HTTPException(
                        status_code=400,
                        message="Potentially unsafe SQL content detected in request body",
                        errors=["SQL injection pattern detected"],
                    )
            elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                form_data = await request.form()
                if _scan_nested(form_data):
                    raise HTTPException(
                        status_code=400,
                        message="Potentially unsafe SQL content detected in form data",
                        errors=["SQL injection pattern detected"],
                    )
        except (ValueError, TypeError):
            pass

    return await call_next(request)


def _contains_sqli(value: str) -> bool:
    """Return True if *value* matches any SQLi pattern."""
    normalized = _normalize(value)
    if not normalized:
        return False
    for pattern in _SQLI_PATTERNS:
        if pattern.search(normalized):
            return True
    return False


def _scan_nested(data: object, depth: int = 0) -> bool:
    """Recursively check nested data for SQLi patterns."""
    if depth > 10:
        return False
    if isinstance(data, str):
        return _contains_sqli(data)
    if isinstance(data, dict):
        for k, v in data.items():
            if _contains_sqli(str(k)) or _scan_nested(v, depth + 1):
                return True
    if isinstance(data, list):
        for item in data:
            if _scan_nested(item, depth + 1):
                return True
    return False


def _request_text_candidates(request: RaftRequest) -> list[str]:
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
    """Decode encoded variants and collapse whitespace/comments."""
    result = value
    for _ in range(3):
        decoded = unquote_plus(unescape(result))
        if decoded == result:
            break
        result = decoded

    # Normalize SQL comments and repeated spaces to simplify signatures.
    result = result.replace("\x00", " ")
    result = re.sub(r"/\*.*?\*/", " ", result, flags=re.DOTALL)
    result = re.sub(r"\s+", " ", result)
    return result.strip()
