import tempfile
import unittest
from pathlib import Path

from raft.cli.main import _scaffold_project


class CliBootstrapStructureTests(unittest.TestCase):
    def test_minimal_rest_bootstrap_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "minimal_project"
            _scaffold_project(
                base,
                project_name="minimal_project",
                use_openapi=True,
                api_style="r",
                use_orm=False,
                use_scheduler=False,
                use_websocket=False,
                use_env=True,
                use_middleware_starter=False,
            )

            self.assertTrue((base / "routes").exists())
            self.assertTrue((base / "schemas").exists())
            self.assertTrue((base / "serializers").exists())
            self.assertFalse((base / "tasks").exists())
            self.assertFalse((base / "ws").exists())
            self.assertFalse((base / "graphql_schema").exists())
            self.assertFalse((base / "middleware").exists())
            self.assertFalse((base / "bootstrap.structure.json").exists())

    def test_full_bootstrap_includes_selected_feature_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "full_project"
            _scaffold_project(
                base,
                project_name="full_project",
                use_openapi=True,
                api_style="g",
                use_orm=True,
                use_scheduler=True,
                use_websocket=True,
                use_env=True,
                use_middleware_starter=True,
            )

            self.assertTrue((base / "tasks").exists())
            self.assertTrue((base / "ws").exists())
            self.assertTrue((base / "graphql_schema").exists())
            self.assertTrue((base / "models").exists())
            self.assertTrue((base / "middleware").exists())
            self.assertFalse((base / "bootstrap.structure.json").exists())


if __name__ == "__main__":
    unittest.main()
