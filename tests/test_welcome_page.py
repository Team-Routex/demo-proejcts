"""Tests for the DEBUG starter welcome page (no routes registered)."""

from __future__ import annotations

import asyncio
import json
import unittest

from raft import Raft, Response
from raft.core.welcome import should_show_welcome


def _request(app: Raft, path: str = "/", method: str = "GET") -> tuple[int, str, bytes]:
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
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }

    asyncio.run(app(scope, receive, send))
    start = sent[0]
    body = sent[1]["body"]
    headers = {
        k.decode().lower(): v.decode()
        for k, v in start.get("headers", [])
    }
    return start["status"], headers.get("content-type", ""), body


class WelcomePageTests(unittest.TestCase):
    def test_should_show_only_in_debug_with_zero_routes(self) -> None:
        self.assertTrue(should_show_welcome(debug=True, route_count=0))
        self.assertFalse(should_show_welcome(debug=False, route_count=0))
        self.assertFalse(should_show_welcome(debug=True, route_count=1))

    def test_empty_app_serves_html_welcome_in_debug(self) -> None:
        app = Raft(
            debug=True,
            auto_discover_routes=False,
            auto_discover_middleware=False,
            auto_discover_tasks=False,
        )
        status, content_type, body = _request(app, "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        html = body.decode("utf-8")
        self.assertIn("Raft", html)
        self.assertIn("@app.get", html)
        self.assertIn("Bricolage Grotesque", html)

    def test_empty_app_json_404_when_not_debug(self) -> None:
        app = Raft(
            debug=False,
            auto_discover_routes=False,
            auto_discover_middleware=False,
            auto_discover_tasks=False,
        )
        status, content_type, body = _request(app, "/")
        self.assertEqual(status, 404)
        self.assertIn("application/json", content_type)
        payload = json.loads(body.decode("utf-8"))
        self.assertFalse(payload["status"])

    def test_welcome_hidden_once_any_route_exists(self) -> None:
        app = Raft(
            debug=True,
            auto_discover_routes=False,
            auto_discover_middleware=False,
            auto_discover_tasks=False,
        )

        @app.get("/health")
        async def health(request):
            return Response.success(message="ok")

        status, content_type, body = _request(app, "/")
        self.assertEqual(status, 404)
        self.assertIn("application/json", content_type)
        self.assertNotIn(b"<!DOCTYPE html>", body)

        status_ok, _, body_ok = _request(app, "/health")
        self.assertEqual(status_ok, 200)
        self.assertEqual(json.loads(body_ok.decode())["message"], "ok")


if __name__ == "__main__":
    unittest.main()
