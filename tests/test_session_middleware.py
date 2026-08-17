"""Session middleware and store behavior."""

from __future__ import annotations

import asyncio
import unittest

from raft import Raft, Response
from raft.config import settings as settings_mod
from raft.session.backend import (
    InMemorySessionStore,
    reset_memory_session_store,
    session_middleware_factory,
)


def _asgi(
    app: Raft,
    path: str,
    *,
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, bytes, list[tuple[bytes, bytes]]]:
    sent: list[dict] = []
    messages = [{"type": "http.request", "body": b"", "more_body": False}]

    async def receive() -> dict:
        if messages:
            return messages.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": headers or [],
        "client": ("127.0.0.1", 1),
    }
    asyncio.run(app(scope, receive, send))
    return sent[0]["status"], sent[1]["body"], sent[0].get("headers", [])


def _cookie_header(response_headers: list[tuple[bytes, bytes]]) -> str | None:
    for k, v in response_headers:
        if k.lower() == b"set-cookie":
            return v.decode().split(";", 1)[0]
    return None


class SessionMiddlewareTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_memory_session_store()
        self._prev_secure = settings_mod.settings.SESSION_COOKIE_SECURE
        settings_mod.settings.SESSION_COOKIE_SECURE = False
        settings_mod.settings.SESSION_BACKEND = "memory"

    def tearDown(self) -> None:
        settings_mod.settings.SESSION_COOKIE_SECURE = self._prev_secure
        reset_memory_session_store()

    def _app(self) -> Raft:
        store = InMemorySessionStore()
        app = Raft(
            debug=True,
            auto_discover_routes=False,
            auto_discover_middleware=False,
            auto_discover_tasks=False,
            enable_sessions=False,
        )
        app.add_middleware(session_middleware_factory(store=store))

        @app.post("/set")
        async def set_session(request):
            request.session["user"] = "ada"
            return Response.success(message="set")

        @app.get("/get")
        async def get_session(request):
            return Response.success(data={"user": request.session.get("user")})

        @app.post("/clear")
        async def clear_session(request):
            request.session.clear()
            return Response.success(message="cleared")

        return app

    def test_session_roundtrip_and_no_cookie_when_empty(self) -> None:
        app = self._app()
        status, _, headers = _asgi(app, "/get")
        self.assertEqual(status, 200)
        self.assertIsNone(_cookie_header(headers))

        status, _, headers = _asgi(app, "/set", method="POST")
        self.assertEqual(status, 200)
        cookie = _cookie_header(headers)
        self.assertIsNotNone(cookie)
        assert cookie is not None
        self.assertIn("HttpOnly", " ".join(
            v.decode() for k, v in headers if k.lower() == b"set-cookie"
        ))

        status, body, _ = _asgi(
            app,
            "/get",
            headers=[(b"cookie", cookie.encode())],
        )
        self.assertEqual(status, 200)
        self.assertIn(b"ada", body)

    def test_clear_deletes_session_cookie(self) -> None:
        app = self._app()
        _, _, headers = _asgi(app, "/set", method="POST")
        cookie = _cookie_header(headers)
        assert cookie is not None

        status, _, headers = _asgi(
            app,
            "/clear",
            method="POST",
            headers=[(b"cookie", cookie.encode())],
        )
        self.assertEqual(status, 200)
        set_cookie = " ".join(
            v.decode() for k, v in headers if k.lower() == b"set-cookie"
        ).lower()
        self.assertIn("max-age=0", set_cookie)


class InMemoryTTLTests(unittest.TestCase):
    def test_ttl_expiry(self) -> None:
        store = InMemorySessionStore()
        prev = settings_mod.settings.SESSION_MAX_AGE
        settings_mod.settings.SESSION_MAX_AGE = 1
        try:
            store.set("abc", {"x": 1})
            self.assertTrue(store.exists("abc"))
            self.assertEqual(store.get("abc"), {"x": 1})
            # Force expiry
            sid = "abc"
            data, _ = store._store[sid]
            store._store[sid] = (data, 0.0)
            self.assertEqual(store.get("abc"), {})
            self.assertFalse(store.exists("abc"))
        finally:
            settings_mod.settings.SESSION_MAX_AGE = prev


if __name__ == "__main__":
    unittest.main()
