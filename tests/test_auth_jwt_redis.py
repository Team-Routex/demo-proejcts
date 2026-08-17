"""Tests for JWT auth and Redis session store."""

from __future__ import annotations

import asyncio
import json
import unittest
from datetime import timedelta

from raft import (
    Raft,
    Response,
    create_access_token,
    decode_access_token,
    require_auth,
)
from raft.config.settings import settings
from raft.core.exceptions import Unauthorized
from raft.session.redis_store import RedisSessionStore


class _FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.data[key] = value
        if ex is not None:
            self.ttls[key] = ex

    def delete(self, key: str) -> None:
        self.data.pop(key, None)
        self.ttls.pop(key, None)

    def exists(self, key: str) -> int:
        return 1 if key in self.data else 0



class JWTAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_jwt = settings.JWT_SECRET
        self._prev_secret = settings.SECRET_KEY
        settings.JWT_SECRET = "test-jwt-secret-key-at-least-32-bytes!!"
        settings.SECRET_KEY = "test-secret-key-at-least-32-bytes!!!!"

    def tearDown(self) -> None:
        settings.JWT_SECRET = self._prev_jwt
        settings.SECRET_KEY = self._prev_secret

    def test_create_and_decode_token(self) -> None:
        token = create_access_token({"sub": "u1", "role": "admin"})
        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], "u1")
        self.assertEqual(payload["role"], "admin")
        self.assertEqual(payload["type"], "access")

    def test_expired_token_raises(self) -> None:
        token = create_access_token("u1", expires_delta=timedelta(seconds=-1))
        with self.assertRaises(Unauthorized):
            decode_access_token(token)

    def test_require_auth_on_route(self) -> None:
        app = Raft(
            debug=True,
            auto_discover_routes=False,
            auto_discover_middleware=False,
            auto_discover_tasks=False,
            enable_sessions=False,
        )
        token = create_access_token({"sub": "42", "name": "Ada"})

        @app.get("/me")
        @require_auth()
        async def me(request):
            return Response.success(data={"user": request.user})

        # Missing token → 401
        status, body = _asgi(app, "/me")
        self.assertEqual(status, 401)

        # Valid token → 200
        status, body = _asgi(
            app,
            "/me",
            headers=[(b"authorization", f"Bearer {token}".encode())],
        )
        self.assertEqual(status, 200)
        payload = json.loads(body.decode())
        self.assertEqual(payload["data"]["user"]["sub"], "42")

    def test_cbv_view_auth(self) -> None:
        from raft import View, route
        from raft.auth import IsAuthenticated, JWTAuthentication

        class MeView(View):
            authentication_classes = [JWTAuthentication]
            permission_classes = [IsAuthenticated]

            async def get(self, request):
                return Response.success(data={"user": request.user})

        app = Raft(
            debug=True,
            auto_discover_routes=False,
            auto_discover_middleware=False,
            auto_discover_tasks=False,
            enable_sessions=False,
        )
        app.add_routes([route("/me/", MeView, methods=["GET"])])
        token = create_access_token({"sub": "99"})

        status, _ = _asgi(app, "/me/")
        self.assertEqual(status, 401)

        status, body = _asgi(
            app,
            "/me/",
            headers=[(b"authorization", f"Bearer {token}".encode())],
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body.decode())["data"]["user"]["sub"], "99")

    def test_method_decorator_auth_kwargs(self) -> None:
        from raft.auth import IsAuthenticated, JWTAuthentication

        app = Raft(
            debug=True,
            auto_discover_routes=False,
            auto_discover_middleware=False,
            auto_discover_tasks=False,
            enable_sessions=False,
        )
        token = create_access_token({"sub": "55"})

        @app.get(
            "/me",
            authentication_classes=[JWTAuthentication],
            permission_classes=[IsAuthenticated],
        )
        async def me(request):
            return Response.success(data={"user": request.user})

        @app.post("/login")
        async def login(request):
            return Response.success(
                data={"access_token": create_access_token({"sub": "x"})}
            )

        status, _ = _asgi(app, "/me")
        self.assertEqual(status, 401)

        status, body = _asgi(
            app,
            "/me",
            headers=[(b"authorization", f"Bearer {token}".encode())],
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body.decode())["data"]["user"]["sub"], "55")

        # Public POST still works without token
        status, _ = _asgi(app, "/login", method="POST")
        self.assertEqual(status, 200)

    def test_table_route_auth_kwargs_on_fbv(self) -> None:
        from raft import route
        from raft.auth import IsAuthenticated, JWTAuthentication

        async def me(request):
            return Response.success(data={"user": request.user})

        app = Raft(
            debug=True,
            auto_discover_routes=False,
            auto_discover_middleware=False,
            auto_discover_tasks=False,
            enable_sessions=False,
        )
        app.add_routes(
            [
                route(
                    "/me/",
                    me,
                    methods=["GET"],
                    authentication_classes=[JWTAuthentication],
                    permission_classes=[IsAuthenticated],
                )
            ]
        )
        token = create_access_token({"sub": "12"})

        status, _ = _asgi(app, "/me/")
        self.assertEqual(status, 401)

        status, body = _asgi(
            app,
            "/me/",
            headers=[(b"authorization", f"Bearer {token}".encode())],
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body.decode())["data"]["user"]["sub"], "12")

    def test_fbv_auth_decorators_in_routes_table(self) -> None:
        from raft import route
        from raft.auth import (
            IsAuthenticated,
            JWTAuthentication,
            authentication_classes,
            permission_classes,
        )

        @authentication_classes([JWTAuthentication])
        @permission_classes([IsAuthenticated])
        async def me(request):
            return Response.success(data={"user": request.user, "has_auth": bool(request.auth)})

        app = Raft(
            debug=True,
            auto_discover_routes=False,
            auto_discover_middleware=False,
            auto_discover_tasks=False,
            enable_sessions=False,
        )
        app.add_routes([route("/me/", me, methods=["GET"])])
        token = create_access_token({"sub": "7"})

        status, _ = _asgi(app, "/me/")
        self.assertEqual(status, 401)

        status, body = _asgi(
            app,
            "/me/",
            headers=[(b"authorization", f"Bearer {token}".encode())],
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode())["data"]
        self.assertEqual(data["user"]["sub"], "7")
        self.assertTrue(data["has_auth"])


class RedisSessionStoreTests(unittest.TestCase):
    def test_redis_session_roundtrip_with_fake_client(self) -> None:
        fake = _FakeRedis()
        store = RedisSessionStore(client=fake)
        asyncio.run(store.set("abc", {"user_id": 7}))
        self.assertEqual(asyncio.run(store.get("abc")), {"user_id": 7})
        self.assertTrue(any("session:abc" in k for k in fake.data))
        self.assertEqual(fake.ttls[next(iter(fake.data))], settings.SESSION_MAX_AGE)
        asyncio.run(store.delete("abc"))
        self.assertEqual(asyncio.run(store.get("abc")), {})


def _asgi(
    app: Raft,
    path: str,
    *,
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, bytes]:
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
    return sent[0]["status"], sent[1]["body"]


if __name__ == "__main__":
    unittest.main()
