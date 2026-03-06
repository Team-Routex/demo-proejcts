"""
raft.session.backend
~~~~~~~~~~~~~~~~~~~~

Server-side in-memory session store with signed cookie transport.

How it works:
    1. A session ID is stored in a signed cookie (``itsdangerous``).
    2. Session data is kept in a server-side dict keyed by session ID.
    3. The session middleware loads data onto ``request.session`` before the
       view runs and persists any changes back after the response.

PROTOTYPE NOTE:
    The in-memory store is suitable for development and single-process
    deployments.  For production:
      - Implement a Redis / database-backed ``SessionStore``
      - Add session expiry / garbage collection
      - Consider session fixation protection
"""

from __future__ import annotations

import secrets
from typing import Any

from itsdangerous import BadSignature, URLSafeTimedSerializer

from raft.config.settings import settings
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.base import CallNext


class InMemorySessionStore:
    """Thread-safe (GIL-protected) in-memory session dict.

    Keys are session IDs, values are arbitrary dicts.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def get(self, session_id: str) -> dict[str, Any]:
        return self._store.setdefault(session_id, {})

    def set(self, session_id: str, data: dict[str, Any]) -> None:
        self._store[session_id] = data

    def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)


# Module-level singleton store.
_store = InMemorySessionStore()


def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY)


def session_middleware_factory(
    store: InMemorySessionStore | None = None,
) -> Any:
    """Return a session middleware function.

    Parameters:
        store: Override the default in-memory store (useful for testing).
    """
    _session_store = store or _store

    async def session_middleware(
        request: RaftRequest, call_next: CallNext
    ) -> RawResponse:
        """Load session before the view, persist after."""
        serializer = _get_serializer()
        cookie_name = settings.SESSION_COOKIE_NAME
        session_id: str | None = None

        # Try to load existing session
        raw_cookie = request.get_cookie(cookie_name)
        if raw_cookie:
            try:
                session_id = serializer.loads(
                    raw_cookie, max_age=settings.SESSION_MAX_AGE
                )
            except BadSignature:
                session_id = None

        if session_id is None:
            session_id = secrets.token_hex(16)

        # Populate request.session
        request.session = _session_store.get(session_id)

        response = await call_next(request)

        # Persist session data
        _session_store.set(session_id, request.session)

        # Set / refresh the session cookie
        signed = serializer.dumps(session_id)
        response.set_cookie(
            name=cookie_name,
            value=signed,
            max_age=settings.SESSION_MAX_AGE,
            httponly=True,
            samesite="Lax",
        )

        return response

    return session_middleware
