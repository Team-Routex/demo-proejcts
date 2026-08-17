"""
raft.auth.jwt
~~~~~~~~~~~~~

JWT access-token helpers for Raft APIs.

Uses ``PyJWT`` with HS256 by default. Secret falls back to ``RAFT_SECRET_KEY``
unless ``RAFT_JWT_SECRET`` is set.

Example::

    from raft import create_access_token, require_auth, Response

    @app.post("/login")
    async def login(request):
        # verify credentials...
        token = create_access_token({"sub": "user-1", "role": "admin"})
        return Response.success(data={"access_token": token, "token_type": "bearer"})

    @app.get("/me")
    @require_auth()
    async def me(request):
        return Response.success(data={"user": request.user})
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from raft.config.settings import settings
from raft.core.exceptions import Unauthorized
from raft.core.request import RaftRequest

try:
    import jwt
except ImportError:  # pragma: no cover
    jwt = None  # type: ignore[assignment]


def _jwt_secret() -> str:
    secret = (getattr(settings, "JWT_SECRET", None) or "").strip()
    resolved = secret or settings.SECRET_KEY
    if not getattr(settings, "DEBUG", True) and (
        resolved == "change-me-in-production" or len(resolved) < 16
    ):
        raise RuntimeError(
            "Insecure JWT secret configured for production. Set RAFT_JWT_SECRET or RAFT_SECRET_KEY."
        )
    return resolved


def _jwt_algorithm() -> str:
    return getattr(settings, "JWT_ALGORITHM", "HS256") or "HS256"


def _require_pyjwt() -> Any:
    if jwt is None:
        raise RuntimeError(
            "PyJWT is required for JWT auth. Install with: pip install PyJWT"
        )
    return jwt


def create_access_token(
    subject: str | dict[str, Any],
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token.

    *subject* may be a string (stored as ``sub``) or a dict of claims
    (must include ``sub`` or it will be added if you pass a string elsewhere —
    prefer ``{"sub": user_id, ...}``).
    """
    pyjwt = _require_pyjwt()
    now = datetime.now(UTC)
    if expires_delta is None:
        minutes = int(getattr(settings, "JWT_EXPIRE_MINUTES", 60) or 60)
        expires_delta = timedelta(minutes=minutes)

    if isinstance(subject, str):
        payload: dict[str, Any] = {"sub": subject}
    else:
        payload = dict(subject)

    payload.update(extra_claims or {})
    payload.setdefault("iat", int(now.timestamp()))
    payload["exp"] = int((now + expires_delta).timestamp())
    payload.setdefault("type", "access")

    return pyjwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT; raises ``Unauthorized`` on failure."""
    pyjwt = _require_pyjwt()
    try:
        payload = pyjwt.decode(
            token,
            _jwt_secret(),
            algorithms=[_jwt_algorithm()],
        )
    except pyjwt.ExpiredSignatureError as exc:
        raise Unauthorized(message="Token has expired") from exc
    except pyjwt.InvalidTokenError as exc:
        raise Unauthorized(message="Invalid token") from exc

    if not isinstance(payload, dict):
        raise Unauthorized(message="Invalid token payload")
    return payload


def get_bearer_token(request: RaftRequest) -> str | None:
    """Extract Bearer token from ``Authorization`` header."""
    header = request.get_header("authorization") or request.get_header("Authorization")
    if not header:
        return None
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def require_auth(
    *,
    optional: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: require a valid JWT and set ``request.user`` to the claims dict.

    Usage::

        @app.get("/secure")
        @require_auth()
        async def secure(request):
            return Response.success(data=request.user)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(request: RaftRequest, *args: Any, **kwargs: Any) -> Any:
                _authenticate_request(request, optional=optional)
                return await func(request, *args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(request: RaftRequest, *args: Any, **kwargs: Any) -> Any:
            _authenticate_request(request, optional=optional)
            return func(request, *args, **kwargs)

        return sync_wrapper

    return decorator


def _authenticate_request(request: RaftRequest, *, optional: bool) -> None:
    token = get_bearer_token(request)
    if not token:
        if optional:
            request.user = None
            return
        raise Unauthorized(message="Missing Bearer token")
    payload = decode_access_token(token)
    request.user = payload
    request.state["user"] = payload


async def jwt_auth_middleware(request: RaftRequest, call_next: Any) -> Any:
    """Optional middleware: attach ``request.user`` when a Bearer token is present.

    Does not reject missing tokens (use ``@require_auth`` on protected routes).
    """
    token = get_bearer_token(request)
    if token:
        try:
            payload = decode_access_token(token)
            request.user = payload
            request.state["user"] = payload
        except Unauthorized:
            request.user = None
    else:
        request.user = None
    return await call_next(request)
