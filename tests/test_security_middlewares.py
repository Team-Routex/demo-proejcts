import asyncio
import unittest
from typing import Any

from raft.core.exceptions import Forbidden, HTTPException
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.middleware.csrf import csrf_middleware
from raft.middleware.sqli import sqli_middleware
from raft.middleware.xss import xss_middleware


class SecurityMiddlewareTests(unittest.TestCase):
    def _make_request(
        self,
        *,
        method: str = "GET",
        path: str = "/",
        query_string: str = "",
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> RaftRequest:
        header_items = [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in (headers or {}).items()
        ]
        messages: list[dict[str, Any]] = [
            {"type": "http.request", "body": body, "more_body": False}
        ]

        async def receive() -> dict[str, Any]:
            if messages:
                return messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        scope: dict[str, Any] = {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": query_string.encode("latin-1"),
            "headers": header_items,
            "path_params": {},
            "client": ("127.0.0.1", 12345),
        }
        return RaftRequest(scope, receive)

    def test_xss_blocks_encoded_query_payload(self) -> None:
        async def runner() -> None:
            request = self._make_request(
                method="GET",
                query_string="q=%3Cscript%3Ealert(1)%3C%2Fscript%3E",
            )

            async def call_next(_: RaftRequest) -> RawResponse:
                return RawResponse(status_code=200)

            await xss_middleware(request, call_next)

        with self.assertRaises(HTTPException):
            asyncio.run(runner())

    def test_sqli_blocks_union_select_in_json_body(self) -> None:
        async def runner() -> None:
            request = self._make_request(
                method="POST",
                headers={"content-type": "application/json"},
                body=b'{"search": "1 UNION SELECT password FROM users"}',
            )

            async def call_next(_: RaftRequest) -> RawResponse:
                return RawResponse(status_code=200)

            await sqli_middleware(request, call_next)

        with self.assertRaises(HTTPException):
            asyncio.run(runner())

    def test_csrf_allows_valid_same_origin_token(self) -> None:
        async def runner() -> RawResponse:
            request = self._make_request(
                method="POST",
                headers={
                    "host": "example.com",
                    "origin": "https://example.com",
                    "x-csrf-token": "abc123",
                },
            )
            request.session["_csrf_token"] = "abc123"

            async def call_next(_: RaftRequest) -> RawResponse:
                return RawResponse(status_code=200)

            return await csrf_middleware(request, call_next)

        response = asyncio.run(runner())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-CSRF-Token"), "abc123")

    def test_csrf_rejects_cross_origin(self) -> None:
        async def runner() -> None:
            request = self._make_request(
                method="POST",
                headers={
                    "host": "example.com",
                    "origin": "https://evil.example",
                    "x-csrf-token": "abc123",
                },
            )
            request.session["_csrf_token"] = "abc123"

            async def call_next(_: RaftRequest) -> RawResponse:
                return RawResponse(status_code=200)

            await csrf_middleware(request, call_next)

        with self.assertRaises(Forbidden):
            asyncio.run(runner())

    def test_csrf_rejects_missing_token_on_mutation(self) -> None:
        async def runner() -> None:
            request = self._make_request(
                method="PATCH",
                headers={"host": "example.com", "origin": "https://example.com"},
            )
            request.session["_csrf_token"] = "abc123"

            async def call_next(_: RaftRequest) -> RawResponse:
                return RawResponse(status_code=200)

            await csrf_middleware(request, call_next)

        with self.assertRaises(Forbidden):
            asyncio.run(runner())


if __name__ == "__main__":
    unittest.main()
