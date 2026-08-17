"""Tests for uniform method decorators and Django-style routes tables."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from raft import Raft, Response, Router, View, include, route
from raft.config.settings import settings
from raft.core.router import Route


def _asgi_get(app: Raft, url_path: str, method: str = "GET") -> dict:
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
        "path": url_path,
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }

    async def run() -> None:
        await app(scope, receive, send)

    asyncio.run(run())
    body = sent[1]["body"]
    return json.loads(body.decode("utf-8"))


class MethodDecoratorRoutingTests(unittest.TestCase):
    def test_app_get_post_put_patch_delete(self) -> None:
        app = Raft(auto_discover_routes=False, auto_discover_middleware=False)

        @app.get("/items")
        async def list_items(request):
            return Response.success(message="get")

        @app.post("/items")
        async def create_item(request):
            return Response.created(message="post")

        @app.put("/items/{id}")
        async def replace_item(request):
            return Response.success(message="put", data={"id": request.path_params["id"]})

        @app.patch("/items/{id}")
        async def patch_item(request):
            return Response.success(message="patch")

        @app.delete("/items/{id}")
        async def delete_item(request):
            return Response.success(message="delete")

        self.assertEqual(_asgi_get(app, "/items")["message"], "get")
        self.assertEqual(_asgi_get(app, "/items", "POST")["message"], "post")
        self.assertEqual(_asgi_get(app, "/items/9", "PUT")["data"]["id"], "9")
        self.assertEqual(_asgi_get(app, "/items/9", "PATCH")["message"], "patch")
        self.assertEqual(_asgi_get(app, "/items/9", "DELETE")["message"], "delete")

    def test_router_method_decorators_with_prefix(self) -> None:
        router = Router(prefix="/api")

        @router.get("/ping")
        async def ping(request):
            return Response.success(message="pong")

        app = Raft(auto_discover_routes=False, auto_discover_middleware=False)
        app.include_router(router)
        self.assertEqual(_asgi_get(app, "/api/ping")["message"], "pong")

    def test_wrong_method_returns_405(self) -> None:
        app = Raft(auto_discover_routes=False, auto_discover_middleware=False)

        @app.get("/only-get")
        async def only_get(request):
            return Response.success()

        payload = _asgi_get(app, "/only-get", "POST")
        self.assertFalse(payload["status"])


class DjangoRouteTableTests(unittest.TestCase):
    def test_route_and_include(self) -> None:
        async def list_users(request):
            return Response.success(message="users")

        async def list_items(request):
            return Response.success(message="items")

        routes = [
            route("/users/", list_users, methods=["GET"], name="users"),
            route(
                "/api/",
                include(
                    [
                        route("/items/", list_items, methods=["GET"], name="items"),
                    ]
                ),
            ),
        ]

        app = Raft(auto_discover_routes=False, auto_discover_middleware=False)
        app.add_routes(routes)

        self.assertEqual(_asgi_get(app, "/users/")["message"], "users")
        self.assertEqual(_asgi_get(app, "/api/items/")["message"], "items")

    def test_route_with_cbv(self) -> None:
        class ItemView(View):
            async def get(self, request):
                return Response.success(message="cbv")

        app = Raft(auto_discover_routes=False, auto_discover_middleware=False)
        app.add_routes([route("/cbv/", ItemView, name="cbv")])
        self.assertEqual(_asgi_get(app, "/cbv/")["message"], "cbv")

    def test_route_with_nested_list_include(self) -> None:
        async def nested(request):
            return Response.success(message="nested")

        app = Raft(auto_discover_routes=False, auto_discover_middleware=False)
        app.add_routes(
            [
                route("/wrap/", [route("/inner/", nested, methods=["GET"])]),
            ]
        )
        self.assertEqual(_asgi_get(app, "/wrap/inner/")["message"], "nested")


class ProjectWideRouteDiscoveryTests(unittest.TestCase):
    def test_discovers_routes_outside_routes_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            api_dir = project_root / "api"
            api_dir.mkdir(parents=True, exist_ok=True)
            (api_dir / "__init__.py").write_text("", encoding="utf-8")
            (api_dir / "users.py").write_text(
                """
from raft import Response, route

async def list_users(request):
    return Response.success(message="from-api")

routes = [
    route("/users/", list_users, methods=["GET"]),
]
""".strip(),
                encoding="utf-8",
            )

            views_dir = project_root / "views"
            views_dir.mkdir(parents=True, exist_ok=True)
            (views_dir / "items.py").write_text(
                """
from raft import Response, Router

router = Router(prefix="/items")

@router.get("/")
async def list_items(request):
    return Response.success(message="from-views")
""".strip(),
                encoding="utf-8",
            )

            original_base_dir = settings.BASE_DIR
            settings.BASE_DIR = project_root
            try:
                with self.assertLogs("raft", level="INFO") as logs:
                    app = Raft(auto_discover_routes=True, auto_discover_middleware=False)
                self.assertEqual(_asgi_get(app, "/users/")["message"], "from-api")
                self.assertEqual(_asgi_get(app, "/items/")["message"], "from-views")
                joined = "\n".join(logs.output)
                self.assertIn("api", joined.replace("\\", "/"))
                self.assertIn("views", joined.replace("\\", "/"))
            finally:
                settings.BASE_DIR = original_base_dir
    def test_autodiscover_routes_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            routes_dir = project_root / "routes"
            routes_dir.mkdir(parents=True, exist_ok=True)
            (routes_dir / "__init__.py").write_text("", encoding="utf-8")
            (routes_dir / "users.py").write_text(
                """
from raft import Response, route

async def list_users(request):
    return Response.success(message="from-routes")

routes = [
    route("/users/", list_users, methods=["GET"]),
]
""".strip(),
                encoding="utf-8",
            )

            original_base_dir = settings.BASE_DIR
            settings.BASE_DIR = project_root
            try:
                with self.assertLogs("raft", level="INFO") as logs:
                    app = Raft(auto_discover_routes=True, auto_discover_middleware=False)
                self.assertEqual(_asgi_get(app, "/users/")["message"], "from-routes")
                self.assertIn("New routes table detected", "\n".join(logs.output))
            finally:
                settings.BASE_DIR = original_base_dir


class LegacyRouteStillWorksTests(unittest.TestCase):
    def test_route_methods_multi(self) -> None:
        app = Raft(auto_discover_routes=False, auto_discover_middleware=False)

        @app.route("/both", methods=["GET", "POST"])
        async def both(request):
            return Response.success(message=request.method)

        self.assertEqual(_asgi_get(app, "/both")["message"], "GET")
        self.assertEqual(_asgi_get(app, "/both", "POST")["message"], "POST")

    def test_add_routes_route_objects(self) -> None:
        async def hello(request):
            return Response.success(message="hello")

        app = Raft(auto_discover_routes=False, auto_discover_middleware=False)
        app.add_routes([Route("/hello", hello, methods=["GET"])])
        self.assertEqual(_asgi_get(app, "/hello")["message"], "hello")


if __name__ == "__main__":
    unittest.main()
