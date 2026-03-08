import tempfile
import unittest
from pathlib import Path

from raft.cli.main import _scaffold_project


class CliWebSocketScaffoldTests(unittest.TestCase):
    def test_scaffold_with_websocket_creates_module_and_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "with_websocket"
            _scaffold_project(
                base,
                project_name="with_websocket",
                use_openapi=True,
                api_style="r",
                use_orm=False,
                use_scheduler=False,
                use_celery=False,
                use_websocket=True,
                use_env=True,
            )

            app_py = (base / "app.py").read_text(encoding="utf-8")
            ws_py = base / "ws" / "chat.py"
            readme = (base / "README.md").read_text(encoding="utf-8")

            self.assertTrue(ws_py.exists())
            self.assertIn("from ws.chat import register_websocket_routes", app_py)
            self.assertIn("register_websocket_routes(app)", app_py)
            self.assertIn("WebSocket: Yes", readme)

    def test_scaffold_without_websocket_skips_module_and_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "without_websocket"
            _scaffold_project(
                base,
                project_name="without_websocket",
                use_openapi=True,
                api_style="r",
                use_orm=False,
                use_scheduler=False,
                use_celery=False,
                use_websocket=False,
                use_env=True,
            )

            app_py = (base / "app.py").read_text(encoding="utf-8")
            ws_py = base / "ws" / "chat.py"
            readme = (base / "README.md").read_text(encoding="utf-8")

            self.assertFalse(ws_py.exists())
            self.assertNotIn("from ws.chat import register_websocket_routes", app_py)
            self.assertNotIn("register_websocket_routes(app)", app_py)
            self.assertIn("WebSocket: No", readme)


if __name__ == "__main__":
    unittest.main()
