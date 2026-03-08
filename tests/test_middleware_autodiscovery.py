import asyncio
import tempfile
import unittest
from pathlib import Path

from raft import Raft
from raft.config.settings import settings


class MiddlewareAutodiscoveryTests(unittest.TestCase):
    def test_autodiscover_loads_custom_middleware_from_project_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            middleware_dir = project_root / "middleware"
            middleware_dir.mkdir(parents=True, exist_ok=True)
            (middleware_dir / "__init__.py").write_text("", encoding="utf-8")
            (middleware_dir / "request_id.py").write_text(
                """
from raft.core.response import RawResponse


async def request_id_middleware(request, call_next):
    response = await call_next(request)
    response.headers[\"X-Autoloaded-Middleware\"] = \"yes\"
    return response
""".strip(),
                encoding="utf-8",
            )

            original_base_dir = settings.BASE_DIR
            settings.BASE_DIR = project_root
            try:
                with self.assertLogs("raft", level="INFO") as logs:
                    app = Raft(auto_discover_middleware=True)

                @app.route("/", methods=["GET"])
                async def index(request):
                    from raft import RaftResponse

                    return RaftResponse.ok(message="ok")

                async def run_request() -> list[tuple[bytes, bytes]]:
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
                        "path": "/",
                        "query_string": b"",
                        "headers": [],
                        "client": ("127.0.0.1", 12345),
                    }
                    await app(scope, receive, send)
                    return sent[0]["headers"]

                headers = asyncio.run(run_request())
                header_dict = {k.decode("latin-1"): v.decode("latin-1") for k, v in headers}
                self.assertEqual(header_dict.get("x-autoloaded-middleware"), "yes")
                joined_logs = "\n".join(logs.output)
                self.assertIn("New middleware detected", joined_logs)
            finally:
                settings.BASE_DIR = original_base_dir


if __name__ == "__main__":
    unittest.main()
