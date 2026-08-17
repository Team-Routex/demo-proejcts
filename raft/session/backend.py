"""
raft.session.backend
~~~~~~~~~~~~~~~~~~~~

Server-side session store with signed cookie transport.

Backends:
    - ``memory`` (default) — in-process dict with TTL
    - ``redis`` — Redis via ``RAFT_REDIS_URL`` (``RAFT_SESSION_BACKEND=redis``)

How it works:
    1. A session ID is stored in a signed cookie (``itsdangerous``).
    2. Session data is kept in a server-side store keyed by session ID.
    3. The session middleware loads data onto ``request.session`` before the
       view runs and persists changes after the response.
"""

from __future__ import annotations

import inspect
import secrets
import time
from typing import Any, Protocol

from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer

from raft.config.settings import settings
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.base import CallNext


class Session(dict[str, Any]):
    """Dict-like session that tracks whether it was mutated."""

    modified: bool
    accessed: bool

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.modified = False
        self.accessed = False
        object.__setattr__(self, "_should_cycle", False)

    def __getitem__(self, key: str) -> Any:
        self.accessed = True
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        self.accessed = True
        return super().get(key, default)

    def __setitem__(self, key: str, value: Any) -> None:
        self.modified = True
        super().__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        self.modified = True
        super().__delitem__(key)

    def clear(self) -> None:
        self.modified = True
        super().clear()

    def pop(self, key: str, *args: Any) -> Any:  # type: ignore[override]
        if key in self:
            self.modified = True
        return super().pop(key, *args)

    def popitem(self) -> tuple[str, Any]:
        self.modified = True
        return super().popitem()

    def setdefault(self, key: str, default: Any = None) -> Any:
        if key not in self:
            self.modified = True
        return super().setdefault(key, default)

    def update(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        self.modified = True
        super().update(*args, **kwargs)

    def cycle_key(self) -> None:
        """Ask middleware to issue a new session ID (call after login)."""
        self.modified = True
        object.__setattr__(self, "_should_cycle", True)


class SessionStore(Protocol):
    """Minimal session persistence interface."""

    def get(self, session_id: str) -> dict[str, Any]: ...

    def set(self, session_id: str, data: dict[str, Any]) -> None: ...

    def delete(self, session_id: str) -> None: ...

    def exists(self, session_id: str) -> bool: ...


class InMemorySessionStore:
    """In-process session store with TTL (``SESSION_MAX_AGE``)."""

    def __init__(self) -> None:
        # session_id -> (data, expires_at_monotonic)
        self._store: dict[str, tuple[dict[str, Any], float]] = {}

    def _purge(self) -> None:
        now = time.monotonic()
        expired = [sid for sid, (_, exp) in self._store.items() if exp <= now]
        for sid in expired:
            self._store.pop(sid, None)

    def exists(self, session_id: str) -> bool:
        self._purge()
        entry = self._store.get(session_id)
        return entry is not None and entry[1] > time.monotonic()

    def get(self, session_id: str) -> dict[str, Any]:
        self._purge()
        entry = self._store.get(session_id)
        if entry is None:
            return {}
        data, expires_at = entry
        if expires_at <= time.monotonic():
            self.delete(session_id)
            return {}
        return dict(data)

    def set(self, session_id: str, data: dict[str, Any]) -> None:
        self._purge()
        if not data:
            self.delete(session_id)
            return
        ttl = max(int(settings.SESSION_MAX_AGE), 1)
        self._store[session_id] = (dict(data), time.monotonic() + ttl)

    def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def clear(self) -> None:
        """Drop all sessions (tests)."""
        self._store.clear()


_memory_store = InMemorySessionStore()


def reset_memory_session_store() -> None:
    """Clear the process-wide memory store (tests)."""
    _memory_store.clear()


def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt="raft-session")


def get_session_store() -> SessionStore:
    """Return the configured session store (``memory`` or ``redis``)."""
    backend = (getattr(settings, "SESSION_BACKEND", "memory") or "memory").strip().lower()
    if backend == "redis":
        from raft.session.redis_store import RedisSessionStore

        return RedisSessionStore()
    return _memory_store


async def _maybe_await(val: Any) -> Any:
    if inspect.isawaitable(val) or hasattr(val, "__await__"):
        return await val
    return val


def session_middleware_factory(
    store: SessionStore | None = None,
) -> Any:
    """Return a session middleware function.

    Parameters:
        store: Override the configured store (useful for testing).
    """
    session_store: SessionStore = store if store is not None else get_session_store()

    async def session_middleware(
        request: RaftRequest, call_next: CallNext
    ) -> RawResponse:
        serializer = _get_serializer()
        cookie_name = settings.SESSION_COOKIE_NAME
        cookie_path = settings.SESSION_COOKIE_PATH or "/"
        session_id: str | None = None
        loaded_existing = False

        raw_cookie = request.get_cookie(cookie_name)
        if raw_cookie:
            try:
                session_id = serializer.loads(
                    raw_cookie, max_age=settings.SESSION_MAX_AGE
                )
            except (BadSignature, BadTimeSignature):
                session_id = None

        if session_id and await _maybe_await(session_store.exists(session_id)):
            loaded_existing = True
            data = await _maybe_await(session_store.get(session_id))
        elif session_id:
            # Stale cookie / expired store entry
            session_id = None
            data = {}
        else:
            data = {}

        if session_id is None:
            session_id = secrets.token_urlsafe(32)

        session = Session(data)
        request.session = session
        request.state["session_id"] = session_id

        response = await call_next(request)

        # Rotate ID after login (session.cycle_key())
        if getattr(session, "_should_cycle", False):
            await _maybe_await(session_store.delete(session_id))
            session_id = secrets.token_urlsafe(32)
            request.state["session_id"] = session_id
            object.__setattr__(session, "_should_cycle", False)
            session.modified = True

        cookie_kwargs: dict[str, Any] = {
            "path": cookie_path,
            "httponly": bool(settings.SESSION_COOKIE_HTTPONLY),
            "secure": bool(settings.SESSION_COOKIE_SECURE),
            "samesite": settings.SESSION_COOKIE_SAMESITE or "Lax",
        }
        domain = settings.SESSION_COOKIE_DOMAIN
        if domain:
            cookie_kwargs["domain"] = domain

        if not session and (loaded_existing or session.modified):
            await _maybe_await(session_store.delete(session_id))
            response.delete_cookie(cookie_name, path=cookie_path)
            return response

        if session.modified or (loaded_existing and session):
            await _maybe_await(session_store.set(session_id, dict(session)))
            signed = serializer.dumps(session_id)
            response.set_cookie(
                name=cookie_name,
                value=signed,
                max_age=settings.SESSION_MAX_AGE,
                **cookie_kwargs,
            )
        elif not loaded_existing and not session:
            # Anonymous empty session — do not set a cookie
            pass

        return response

    return session_middleware
