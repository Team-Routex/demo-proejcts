import asyncio
import tempfile
import unittest
from pathlib import Path

from raft import Raft
from raft.config.settings import settings


class TaskAutodiscoveryTests(unittest.TestCase):
    def test_autodiscover_loads_periodic_tasks_from_tasks_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            tasks_dir = project_root / "tasks"
            tasks_dir.mkdir(parents=True, exist_ok=True)
            (tasks_dir / "__init__.py").write_text("", encoding="utf-8")
            (tasks_dir / "jobs.py").write_text(
                """
from raft.tasks import periodic_task


@periodic_task(every=0.05, repeat=False, run_immediately=True)
async def cleanup_task():
    return None


def build_welcome_message(name: str) -> str:
    return f\"Welcome, {name}!\"
""".strip(),
                encoding="utf-8",
            )

            original_base_dir = settings.BASE_DIR
            try:
                settings.BASE_DIR = project_root
                with self.assertLogs("raft", level="INFO") as logs:
                    app = Raft(auto_discover_tasks=True, auto_discover_middleware=False)

                task_names = [t.name for t in app.scheduler.tasks]
                self.assertIn("cleanup_task", task_names)

                joined_logs = "\n".join(logs.output)
                self.assertIn("New task detected", joined_logs)
            finally:
                settings.BASE_DIR = original_base_dir

    def test_tasks_can_be_imported_and_used_in_views(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            tasks_dir = project_root / "tasks"
            tasks_dir.mkdir(parents=True, exist_ok=True)
            (tasks_dir / "__init__.py").write_text("", encoding="utf-8")
            (tasks_dir / "helpers.py").write_text(
                """
def build_welcome_message(name: str) -> str:
    return f\"Welcome, {name}!\"
""".strip(),
                encoding="utf-8",
            )

            import importlib.util

            spec = importlib.util.spec_from_file_location("tasks.helpers", tasks_dir / "helpers.py")
            module = importlib.util.module_from_spec(spec)
            assert spec is not None and spec.loader is not None
            spec.loader.exec_module(module)
            self.assertEqual(module.build_welcome_message("Raft"), "Welcome, Raft!")


if __name__ == "__main__":
    unittest.main()
