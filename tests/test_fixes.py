"""
tests.test_fixes
~~~~~~~~~~~~~~~~~

Unit tests validating fixes for code review items.
"""

from __future__ import annotations

import asyncio
import time
import unittest

from raft import Raft, Response
from raft.auth.jwt import _jwt_secret
from raft.config.settings import settings
from raft.core.request import _parse_multipart
from raft.core.response import RawResponse
from raft.core.type_enforcement import _coerce, _unwrap_optional
from raft.middleware.cors import cors_middleware
from raft.middleware.csrf import _get_request_csrf_token
from raft.middleware.rate_limit import _MemoryRateLimiter
from raft.middleware.sqli import sqli_middleware
from raft.resilience.circuit_breaker import CircuitBreaker
from raft.websocket.manager import WebSocketManager


class SecurityFixesTests(unittest.TestCase):
    def test_production_secret_key_validation(self) -> None:
        prev_debug = settings.DEBUG
        prev_secret = settings.SECRET_KEY
        try:
            settings.DEBUG = False
            settings.SECRET_KEY = "change-me-in-production"
            with self.assertRaises(RuntimeError):
                _jwt_secret()
        finally:
            settings.DEBUG = prev_debug
            settings.SECRET_KEY = prev_secret

    def test_csrf_does_not_use_cookie_as_submitted_token(self) -> None:
        class DummyRequest:
            def get_header(self, name: str, default: str | None = None) -> str | None:
                return None

            def get_cookie(self, name: str, default: str | None = None) -> str | None:
                return "stolen_cookie_token"

        req = DummyRequest()
        token = asyncio.run(_get_request_csrf_token(req))  # type: ignore[arg-type]
        self.assertIsNone(token)

    def test_sqli_allows_hex_colors(self) -> None:
        app = Raft(debug=True, enable_sqli=True)

        @app.post("/test-color")
        async def handle(req):
            data = await req.json()
            return Response.success(data=data)

        # Simulating request with hex color
        class FakeRequest:
            query_string = ""
            query_params = {}
            path_params = {}
            headers = {}
            method = "POST"

            def get_header(self, name, default=None):
                if name.lower() == "content-type":
                    return "application/json"
                return default

            async def json(self):
                return {"color": "#FFFFFF", "tag": "#section1"}

        async def call_next(r):
            return Response.success()

        resp = asyncio.run(sqli_middleware(FakeRequest(), call_next))  # type: ignore[arg-type]
        self.assertEqual(resp.status_code, 200)

    def test_multipart_filename_traversal_sanitized(self) -> None:
        raw_body = (
            b"------raft\r\n"
            b'Content-Disposition: form-data; name="file"; filename="../../etc/evil.sh"\r\n'
            b"Content-Type: application/x-sh\r\n\r\n"
            b"echo 1\r\n"
            b"------raft--\r\n"
        )
        _, files = _parse_multipart(raw_body, "multipart/form-data; boundary=----raft")
        self.assertIn("file", files)
        self.assertEqual(files["file"].filename, "evil.sh")

    def test_cors_returns_wildcard_when_configured_with_wildcard(self) -> None:
        class DummyRequest:
            method = "GET"

            def get_header(self, name: str, default: str = "") -> str:
                if name.lower() == "origin":
                    return "https://untrusted-site.com"
                return default

        async def call_next(_: Any) -> RawResponse:
            return RawResponse(status_code=200)

        prev_origins = settings.CORS_ALLOWED_ORIGINS
        try:
            settings.CORS_ALLOWED_ORIGINS = ["*"]
            resp = asyncio.run(cors_middleware(DummyRequest(), call_next))  # type: ignore[arg-type]
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
        finally:
            settings.CORS_ALLOWED_ORIGINS = prev_origins

    def test_cors_sets_vary_origin_when_specific_origin_allowed(self) -> None:
        class DummyRequest:
            method = "GET"

            def get_header(self, name: str, default: str = "") -> str:
                if name.lower() == "origin":
                    return "https://trusted-site.com"
                return default

        async def call_next(_: Any) -> RawResponse:
            return RawResponse(status_code=200)

        prev_origins = settings.CORS_ALLOWED_ORIGINS
        try:
            settings.CORS_ALLOWED_ORIGINS = ["https://trusted-site.com"]
            resp = asyncio.run(cors_middleware(DummyRequest(), call_next))  # type: ignore[arg-type]
            self.assertEqual(
                resp.headers.get("Access-Control-Allow-Origin"), "https://trusted-site.com"
            )
            self.assertIn("Origin", resp.headers.get("Vary", ""))
        finally:
            settings.CORS_ALLOWED_ORIGINS = prev_origins

    def test_type_enforcement_union_syntax(self) -> None:
        inner = _unwrap_optional(int | None)
        self.assertIs(inner, int)
        coerced, err = _coerce("val", "42", int | None)
        self.assertIsNone(err)
        self.assertEqual(coerced, 42)
        coerced_none, err_none = _coerce("val", "", int | None)
        self.assertIsNone(err_none)
        self.assertIsNone(coerced_none)

    def test_circuit_breaker_preserves_wrapped_metadata(self) -> None:
        breaker = CircuitBreaker("test-meta")

        @breaker
        async def sample_task(x: int) -> int:
            """Sample docstring."""
            return x * 2

        self.assertEqual(sample_task.__name__, "sample_task")
        self.assertEqual(sample_task.__doc__, "Sample docstring.")



class RateLimiterFixesTests(unittest.TestCase):
    def test_memory_limiter_evicts_stale_keys(self) -> None:
        limiter = _MemoryRateLimiter(max_requests=10, window_seconds=0.01)
        for i in range(60):
            limiter.allow(f"ip-{i}")

        self.assertGreater(len(limiter._hits), 50)
        time.sleep(0.02)
        # Next call triggers dead key eviction
        limiter.allow("ip-trigger")
        self.assertLessEqual(len(limiter._hits), 10)


class WebSocketManagerFixesTests(unittest.TestCase):
    def test_broadcast_handles_individual_send_error(self) -> None:
        manager = WebSocketManager()

        class MockWS:
            def __init__(self, should_fail: bool):
                self.should_fail = should_fail
                self.received = []

            async def send_text(self, message: str) -> None:
                if self.should_fail:
                    raise ConnectionError("Disconnected")
                self.received.append(message)

        ws1 = MockWS(should_fail=True)
        ws2 = MockWS(should_fail=False)

        manager.connect(ws1)  # type: ignore[arg-type]
        manager.connect(ws2)  # type: ignore[arg-type]

        asyncio.run(manager.broadcast("hello"))
        self.assertEqual(ws2.received, ["hello"])
        self.assertNotIn(ws1, manager._connections)
        self.assertIn(ws2, manager._connections)


if __name__ == "__main__":
    unittest.main()
