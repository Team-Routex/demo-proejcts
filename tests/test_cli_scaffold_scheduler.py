import tempfile
import unittest
from pathlib import Path

from raft.cli.main import _scaffold_project


class CliSchedulerScaffoldTests(unittest.TestCase):
    def test_scaffold_with_scheduler_creates_module_and_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "with_scheduler"
            _scaffold_project(
                base,
                project_name="with_scheduler",
                use_openapi=True,
                use_orm=False,
                use_scheduler=True,
                use_websocket=False,
                use_env=True,
            )

            app_py = (base / "app.py").read_text()
            readme = (base / "README.md").read_text(encoding="utf-8")
            scheduler_py = base / "tasks" / "scheduler.py"
            periodic_py = base / "tasks" / "periodic.py"

            self.assertTrue(scheduler_py.exists())
            self.assertTrue(periodic_py.exists())
            self.assertIn("from tasks.scheduler import register_scheduled_tasks", app_py)
            self.assertIn("register_scheduled_tasks(app)", app_py)
            self.assertIn("Built-in Task Scheduler: Yes", readme)

    def test_scaffold_without_scheduler_skips_module_and_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "without_scheduler"
            _scaffold_project(
                base,
                project_name="without_scheduler",
                use_openapi=True,
                use_orm=False,
                use_scheduler=False,
                use_websocket=False,
                use_env=True,
            )

            app_py = (base / "app.py").read_text()
            readme = (base / "README.md").read_text(encoding="utf-8")
            scheduler_py = base / "tasks" / "scheduler.py"
            periodic_py = base / "tasks" / "periodic.py"

            self.assertFalse(scheduler_py.exists())
            self.assertFalse(periodic_py.exists())
            self.assertNotIn("from tasks.scheduler import register_scheduled_tasks", app_py)
            self.assertNotIn("register_scheduled_tasks(app)", app_py)
            self.assertIn("Built-in Task Scheduler: No", readme)


if __name__ == "__main__":
    unittest.main()
