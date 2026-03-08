import tempfile
import unittest
from pathlib import Path

from raft.cli.main import _scaffold_project


class CliMiddlewareStarterScaffoldTests(unittest.TestCase):
    def test_scaffold_with_middleware_starter_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "with_middleware_starter"
            _scaffold_project(
                base,
                project_name="with_middleware_starter",
                use_openapi=True,
                api_style="r",
                use_orm=False,
                use_scheduler=False,
                use_celery=False,
                use_websocket=False,
                use_env=True,
                use_middleware_starter=True,
            )

            starter_file = base / "middleware" / "request_id.py"
            readme = (base / "README.md").read_text(encoding="utf-8")

            self.assertTrue(starter_file.exists())
            self.assertIn("request_id_middleware", starter_file.read_text(encoding="utf-8"))
            self.assertIn("Custom Middleware Starter: Yes", readme)

    def test_scaffold_without_middleware_starter_skips_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "without_middleware_starter"
            _scaffold_project(
                base,
                project_name="without_middleware_starter",
                use_openapi=True,
                api_style="r",
                use_orm=False,
                use_scheduler=False,
                use_celery=False,
                use_websocket=False,
                use_env=True,
                use_middleware_starter=False,
            )

            starter_file = base / "middleware" / "request_id.py"
            readme = (base / "README.md").read_text(encoding="utf-8")

            self.assertFalse(starter_file.exists())
            self.assertIn("Custom Middleware Starter: No", readme)


if __name__ == "__main__":
    unittest.main()
