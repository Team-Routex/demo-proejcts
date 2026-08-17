"""OpenAPI docs access control and Swagger/ReDoc serving."""

from __future__ import annotations

import asyncio
import base64
import json
import unittest

from raft import Raft, Response
from raft.openapi.router import OpenAPIRouter


def _asgi(
    app: Raft,
    path: str,
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, bytes, dict[str, str]]:
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
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": headers or [],
        "client": ("127.0.0.1", 1),
    }
    asyncio.run(app(scope, receive, send))
    status = sent[0]["status"]
    hdrs = {
        k.decode().lower(): v.decode()
        for k, v in sent[0].get("headers", [])
    }
    body = sent[1]["body"] if len(sent) > 1 else b""
    return status, body, hdrs


def _basic(user: str, password: str) -> list[tuple[bytes, bytes]]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return [(b"authorization", f"Basic {token}".encode())]


class OpenAPIDocsAccessTests(unittest.TestCase):
    def _app(self, **openapi_kwargs: object) -> Raft:
        app = Raft(
            debug=True,
            auto_discover_routes=False,
            auto_discover_middleware=False,
            auto_discover_tasks=False,
            enable_sessions=False,
        )

        @app.get("/ping")
        async def ping(request):
            return Response.success(message="pong")

        openapi = OpenAPIRouter(app, title="Test", **openapi_kwargs)  # type: ignore[arg-type]
        app.include_router(openapi.router)
        return app

    def test_public_docs_and_schema(self) -> None:
        app = self._app(docs_enabled=True, docs_visibility="public")
        status, body, _ = _asgi(app, "/docs")
        self.assertEqual(status, 200)
        self.assertIn(b"swagger-ui", body)

        status, body, _ = _asgi(app, "/openapi.json")
        self.assertEqual(status, 200)
        spec = json.loads(body.decode())
        self.assertIn("/ping", spec["paths"])

        status, body, _ = _asgi(app, "/redoc")
        self.assertEqual(status, 200)
        self.assertIn(b"redoc", body.lower())

    def test_disabled_docs_return_404(self) -> None:
        app = self._app(docs_enabled=False)
        for path in ("/docs", "/redoc", "/openapi.json"):
            status, _, _ = _asgi(app, path)
            self.assertEqual(status, 404, path)

    def test_visibility_disabled_alias(self) -> None:
        app = self._app(docs_visibility="disabled")
        status, _, _ = _asgi(app, "/docs")
        self.assertEqual(status, 404)

    def test_basic_auth_username_and_password(self) -> None:
        app = self._app(
            docs_enabled=True,
            docs_visibility="public",
            docs_username="docs",
            docs_password="s3cret",
        )
        status, _, hdrs = _asgi(app, "/docs")
        self.assertEqual(status, 401)
        self.assertIn("basic", hdrs.get("www-authenticate", "").lower())

        status, _, _ = _asgi(app, "/docs", headers=_basic("wrong", "s3cret"))
        self.assertEqual(status, 401)

        status, body, _ = _asgi(app, "/docs", headers=_basic("docs", "s3cret"))
        self.assertEqual(status, 200)
        self.assertIn(b"swagger-ui", body)

        status, body, _ = _asgi(
            app, "/openapi.json", headers=_basic("docs", "s3cret")
        )
        self.assertEqual(status, 200)
        self.assertIn("/ping", json.loads(body.decode())["paths"])

    def test_private_defaults_username_admin(self) -> None:
        app = self._app(
            docs_visibility="private",
            docs_password="pw",
            docs_username="",
        )
        status, _, _ = _asgi(app, "/docs", headers=_basic("admin", "pw"))
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
