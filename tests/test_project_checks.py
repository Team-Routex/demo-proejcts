import tempfile
import unittest
from pathlib import Path

from raft.cli.project_checks import collect_health_checks
from raft.cli.main import _scaffold_project


class ProjectChecksTests(unittest.TestCase):
    def test_minimal_scaffold_passes_core_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "chk"
            _scaffold_project(
                base,
                project_name="chk",
                use_openapi=False,
                use_orm=False,
                use_scheduler=False,
                use_websocket=False,
                use_env=True,
                use_middleware_starter=False,
            )
            env_path = base / ".env"
            env_path.write_text(
                env_path.read_text(encoding="utf-8").replace(
                    "RAFT_SECRET_KEY=change-me-to-a-random-secret",
                    "RAFT_SECRET_KEY=test-secret-" + ("x" * 48),
                ),
                encoding="utf-8",
            )
            rows = collect_health_checks(base)
            labels = {r[0] for r in rows}
            self.assertIn("pyproject.toml", labels)
            self.assertIn("ASGI app import (module + app)", labels)
            failed = [r for r in rows if not r[1]]
            self.assertEqual(
                failed,
                [],
                msg="Expected minimal REST scaffold to pass checks: " + repr(failed),
            )


if __name__ == "__main__":
    unittest.main()
