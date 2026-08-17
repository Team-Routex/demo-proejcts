"""
tests.test_type_enforcement
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tests for automatic parameter binding and type enforcement in Raft.

Strict mode  → parameter has a type annotation  → coerce, 422 on failure
Lax mode     → parameter has no type annotation → raw value, no 422 raised
"""
from __future__ import annotations

import asyncio
import json
import unittest

from raft import Raft, Response


# ---------------------------------------------------------------------------
# ASGI test helper
# ---------------------------------------------------------------------------

def _asgi(
    app: Raft,
    path: str,
    *,
    method: str = "GET",
    query: str = "",
    body: dict | None = None,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, dict]:
    """Run a single ASGI request and return (status_code, json_body)."""
    raw_body = json.dumps(body).encode() if body is not None else b""
    sent: list[dict] = []

    scope = {
        "type": "http",
        "method": method.upper(),
        "path": path,
        "query_string": query.encode(),
        "headers": headers or (
            [(b"content-type", b"application/json")] if body is not None else []
        ),
        "client": ("127.0.0.1", 1234),
    }

    async def receive() -> dict:
        return {"type": "http.request", "body": raw_body, "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    async def _run() -> None:
        await app(scope, receive, send)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()

    status = sent[0]["status"]
    payload = json.loads(sent[1]["body"].decode())
    return status, payload


def _make_app(**kwargs) -> Raft:
    return Raft(
        debug=True,
        auto_discover_routes=False,
        auto_discover_middleware=False,
        auto_discover_tasks=False,
        enable_sessions=False,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Tests: STRICT mode (annotated parameters)
# ---------------------------------------------------------------------------

class StrictTypeEnforcementTests(unittest.TestCase):

    def test_path_param_coerced_to_int(self):
        """Annotated path param 'id: int' is automatically coerced from string."""
        app = _make_app()

        @app.get("/items/{item_id}")
        async def get_item(request, item_id: int):
            return Response.success(data={"item_id": item_id, "type": type(item_id).__name__})

        status, body = _asgi(app, "/items/42")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["item_id"], 42)
        self.assertEqual(body["data"]["type"], "int")

    def test_invalid_int_returns_422(self):
        """Annotated 'item_id: int' with non-numeric string → auto 422."""
        app = _make_app()

        @app.get("/items/{item_id}")
        async def get_item(request, item_id: int):
            return Response.success(data={"item_id": item_id})

        status, body = _asgi(app, "/items/not-a-number")
        self.assertEqual(status, 422)
        self.assertIn("item_id", body.get("errors", [""])[0])

    def test_query_param_coerced_to_float(self):
        """Annotated query param 'price: float' is coerced from raw query string."""
        app = _make_app()

        @app.get("/products")
        async def list_products(request, price: float = 0.0):
            return Response.success(data={"price": price, "type": type(price).__name__})

        status, body = _asgi(app, "/products", query="price=9.99")
        self.assertEqual(status, 200)
        self.assertAlmostEqual(body["data"]["price"], 9.99)
        self.assertEqual(body["data"]["type"], "float")

    def test_annotated_bool_coercion(self):
        """'active: bool' query param coerces 'true'/'false' strings."""
        app = _make_app()

        @app.get("/status")
        async def check_status(request, active: bool = False):
            return Response.success(data={"active": active})

        status, body = _asgi(app, "/status", query="active=true")
        self.assertEqual(status, 200)
        self.assertIs(body["data"]["active"], True)

    def test_missing_required_annotated_param_returns_422(self):
        """A required annotated param with no default and no input → 422."""
        app = _make_app()

        @app.get("/search")
        async def search(request, q: str):
            return Response.success(data={"q": q})

        status, body = _asgi(app, "/search")
        self.assertEqual(status, 422)
        self.assertTrue(any("q" in e for e in body.get("errors", [])))

    def test_annotated_default_used_when_absent(self):
        """Optional annotated param uses declared default if absent."""
        app = _make_app()

        @app.get("/results")
        async def results(request, page: int = 1, limit: int = 20):
            return Response.success(data={"page": page, "limit": limit})

        status, body = _asgi(app, "/results")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["page"], 1)
        self.assertEqual(body["data"]["limit"], 20)

    def test_multiple_annotated_path_and_query_params(self):
        """Mix of path and query params, both annotated, both coerced."""
        app = _make_app()

        @app.get("/users/{user_id}/posts")
        async def user_posts(request, user_id: int, page: int = 1):
            return Response.success(data={"user_id": user_id, "page": page})

        status, body = _asgi(app, "/users/7/posts", query="page=3")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["user_id"], 7)
        self.assertEqual(body["data"]["page"], 3)


# ---------------------------------------------------------------------------
# Tests: LAX mode (unannotated parameters)
# ---------------------------------------------------------------------------

class LaxTypeEnforcementTests(unittest.TestCase):

    def test_unannotated_param_receives_raw_string(self):
        """Unannotated path param gets raw string value, never a 422."""
        app = _make_app()

        @app.get("/items/{item_id}")
        async def get_item(request, item_id):
            return Response.success(data={"item_id": item_id, "type": type(item_id).__name__})

        status, body = _asgi(app, "/items/hello")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["item_id"], "hello")
        self.assertEqual(body["data"]["type"], "str")

    def test_unannotated_non_numeric_does_not_422(self):
        """Non-numeric value for unannotated param passes through without error."""
        app = _make_app()

        @app.get("/items/{item_id}")
        async def get_item(request, item_id):
            return Response.success(data={"item_id": item_id})

        status, _ = _asgi(app, "/items/not-a-number")
        self.assertEqual(status, 200)

    def test_unannotated_with_default(self):
        """Unannotated param with default uses raw value when present."""
        app = _make_app()

        @app.get("/search")
        async def search(request, q=""):
            return Response.success(data={"q": q})

        status, body = _asgi(app, "/search", query="q=hello world")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["q"], "hello world")


# ---------------------------------------------------------------------------
# Tests: MIXED mode (some annotated, some not)
# ---------------------------------------------------------------------------

class MixedTypeEnforcementTests(unittest.TestCase):

    def test_mixed_params_strict_and_lax(self):
        """Annotated param coerced; unannotated param is raw string."""
        app = _make_app()

        @app.get("/products/{category}")
        async def list_by_category(request, category, page: int = 1):
            return Response.success(data={
                "category": category,
                "category_type": type(category).__name__,
                "page": page,
                "page_type": type(page).__name__,
            })

        status, body = _asgi(app, "/products/electronics", query="page=2")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["category"], "electronics")
        self.assertEqual(body["data"]["category_type"], "str")
        self.assertEqual(body["data"]["page"], 2)
        self.assertEqual(body["data"]["page_type"], "int")

    def test_invalid_typed_param_422_even_with_unannotated_sibling(self):
        """Strict 422 fires on the annotated param even if another is unannotated."""
        app = _make_app()

        @app.get("/products/{category}")
        async def list_by_category(request, category, page: int = 1):
            return Response.success(data={"category": category, "page": page})

        status, _ = _asgi(app, "/products/electronics", query="page=notanint")
        self.assertEqual(status, 422)


# ---------------------------------------------------------------------------
# Tests: Request object injection
# ---------------------------------------------------------------------------

class RequestInjectionTests(unittest.TestCase):

    def test_request_always_injected(self):
        """The 'request' parameter is automatically injected."""
        app = _make_app()

        @app.get("/ping")
        async def ping(request):
            return Response.success(data={"method": request.method})

        status, body = _asgi(app, "/ping")
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["method"], "GET")

    def test_handler_with_only_request(self):
        """Classic single-arg handler still works after type enforcement wiring."""
        app = _make_app()

        @app.post("/echo")
        async def echo(request):
            data = await request.json()
            return Response.success(data=data)

        status, body = _asgi(app, "/echo", method="POST", body={"msg": "hi"})
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["msg"], "hi")


# ---------------------------------------------------------------------------
# Tests: Mypy startup & route analysis integration
# ---------------------------------------------------------------------------

class MypyStartupCheckTests(unittest.TestCase):

    def test_typecheck_routes_method(self):
        """Raft.typecheck_routes() invokes Mypy route static analysis cleanly."""
        app = _make_app()

        @app.get("/demo")
        async def demo(request, val: int = 10):
            return Response.success(data={"val": val})

        stdout, stderr, status = app.typecheck_routes()
        self.assertIsInstance(stdout, str)
        self.assertIsInstance(stderr, str)
        self.assertIsInstance(status, int)


if __name__ == "__main__":
    unittest.main()

