"""
raft.middleware.sqli
~~~~~~~~~~~~~~~~~~~~

SQL Injection avoidance middleware.

Scans query parameters and JSON body values for common SQL injection
patterns and rejects suspicious requests with a 400 response.

PROTOTYPE NOTE:
    This is a *heuristic, defense-in-depth* layer — NOT a replacement for
    parameterised queries.  The primary defense against SQL injection is
    **always** using parameterised statements / ORM query builders.

    For production hardening:
      - Use a WAF (Web Application Firewall) for real regex-based SQLi detection
      - Ensure all database access uses parameterised queries
      - Treat this middleware as an early-warning tripwire, not a guarantee
"""

from __future__ import annotations

import re

from raft.core.exceptions import HTTPException
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.base import CallNext

# Common SQL injection indicators (case-insensitive).
_SQLI_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(\b(UNION\s+SELECT|SELECT\s+\*|DROP\s+TABLE|INSERT\s+INTO)\b)", re.IGNORECASE),
    re.compile(r"(--|;)\s*(DROP|ALTER|DELETE|UPDATE|INSERT)\b", re.IGNORECASE),
    re.compile(r"'\s*(OR|AND)\s+[\d'\"=]", re.IGNORECASE),
    re.compile(r"(EXEC(\s|\+)+(S|X)P\w+)", re.IGNORECASE),
]


async def sqli_middleware(request: RaftRequest, call_next: CallNext) -> RawResponse:
    """Reject requests containing obvious SQL injection patterns."""

    # Scan query string
    if _contains_sqli(request.query_string):
        raise HTTPException(
            status_code=400,
            message="Potentially unsafe SQL content detected in query parameters",
            errors=["SQL injection pattern detected"],
        )

    # Scan JSON body for unsafe methods
    if request.method.upper() in {"POST", "PUT", "PATCH"}:
        content_type = request.get_header("content-type", "")
        if "json" in content_type:
            try:
                body = await request.json()
                if body and _scan_values(body):
                    raise HTTPException(
                        status_code=400,
                        message="Potentially unsafe SQL content detected in request body",
                        errors=["SQL injection pattern detected"],
                    )
            except (ValueError, TypeError):
                pass

    return await call_next(request)


def _contains_sqli(value: str) -> bool:
    """Return True if *value* matches any SQLi pattern."""
    for pattern in _SQLI_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _scan_values(data: object, depth: int = 0) -> bool:
    """Recursively check dict/list string values for SQLi patterns."""
    if depth > 10:
        return False
    if isinstance(data, str):
        return _contains_sqli(data)
    if isinstance(data, dict):
        for v in data.values():
            if _scan_values(v, depth + 1):
                return True
    if isinstance(data, list):
        for item in data:
            if _scan_values(item, depth + 1):
                return True
    return False
