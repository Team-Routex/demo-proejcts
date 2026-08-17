"""Rate limiting middleware tests."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from raft.core.exceptions import HTTPException
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.rate_limit import rate_limit_middleware, reset_rate_limiter


class RateLimitMiddlewareTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_rate_limiter()

    def tearDown(self) -> None:
        reset_rate_limiter()

    def _request(self, ip: str = "203.0.113.10") -> RaftRequest:
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [(b"x-forwarded-for", ip.encode())],
            "path_params": {},
            "client": ("127.0.0.1", 12345),
        }
        return RaftRequest(scope, receive)

    def test_blocks_after_limit(self) -> None:
        async def run() -> None:
            async def call_next(_: RaftRequest) -> RawResponse:
                return RawResponse(status_code=200)

            with patch("raft.middleware.rate_limit.settings") as mock_settings:
                mock_settings.RATE_LIMIT_ENABLED = True
                mock_settings.RATE_LIMIT_REQUESTS = 2
                mock_settings.RATE_LIMIT_WINDOW_SECONDS = 60
                mock_settings.RATE_LIMIT_BACKEND = "memory"
                mock_settings.REDIS_URL = ""

                req = self._request()
                await rate_limit_middleware(req, call_next)
                await rate_limit_middleware(req, call_next)
                with self.assertRaises(HTTPException) as ctx:
                    await rate_limit_middleware(req, call_next)
                self.assertEqual(ctx.exception.status_code, 429)

        asyncio.run(run())

    def test_disabled_passes_through(self) -> None:
        async def run() -> None:
            async def call_next(_: RaftRequest) -> RawResponse:
                return RawResponse(status_code=204)

            with patch("raft.middleware.rate_limit.settings") as mock_settings:
                mock_settings.RATE_LIMIT_ENABLED = False
                resp = await rate_limit_middleware(self._request(), call_next)
                self.assertEqual(resp.status_code, 204)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
