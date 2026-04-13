import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from raft import Raft
from raft.config.settings import settings


class RoutesAutodiscoveryTests(unittest.TestCase):
    def test_autodiscover_loads_router_from_routes_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            routes_dir = project_root / "routes"
            routes_dir.mkdir(parents=True, exist_ok=True)
            (routes_dir / "__init__.py").write_text("", encoding="utf-8")
            (routes_dir / "items.py").write_text(
                """
from raft import RaftResponse, Router

router = Router(prefix="/items")


@router.route("/", methods=["GET"])
async def list_items(request):
    return RaftResponse.ok(message="items", data=[])
""".strip(),
                encoding="utf-8",
            )

            original_base_dir = settings.BASE_DIR
            settings.BASE_DIR = project_root
            try:
                with self.assertLogs("raft", level="INFO") as logs:
                    app = Raft(auto_discover_routes=True, auto_discover_middleware=False)

                async def run_request() -> bytes:
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
                        "path": "/items/",
                        "query_string": b"",
                        "headers": [],
                        "client": ("127.0.0.1", 12345),
                    }
                    await app(scope, receive, send)
                    return sent[1]["body"]

                body = asyncio.run(run_request())
                payload = json.loads(body.decode("utf-8"))
                self.assertTrue(payload["status"])
                self.assertEqual(payload["message"], "items")

                joined = "\n".join(logs.output)
                self.assertIn("New router detected", joined)
            finally:
                settings.BASE_DIR = original_base_dir

    def test_autodiscover_skips_init_and_private_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            routes_dir = project_root / "routes"
            routes_dir.mkdir(parents=True, exist_ok=True)
            (routes_dir / "__init__.py").write_text("router = None\n", encoding="utf-8")
            (routes_dir / "_private.py").write_text(
                "from raft import Router\nrouter = Router(prefix='/nope')\n",
                encoding="utf-8",
            )

            original_base_dir = settings.BASE_DIR
            settings.BASE_DIR = project_root
            try:
                app = Raft(auto_discover_routes=True, auto_discover_middleware=False)
                result = app.router.resolve("/nope/", "GET")
                self.assertIsNone(result)
            finally:
                settings.BASE_DIR = original_base_dir


if __name__ == "__main__":
    unittest.main()
