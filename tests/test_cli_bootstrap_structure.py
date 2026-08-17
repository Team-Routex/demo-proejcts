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
                use_pydantic=False,
                use_openapi=True,
                use_orm=False,
                use_scheduler=False,
                use_websocket=False,
                use_env=True,
                use_middleware_starter=False,
            )

            self.assertTrue((base / "routes").exists())
            routes_init = (base / "routes" / "__init__.py").read_text(encoding="utf-8")
            self.assertIn("anywhere", routes_init.lower())
            app_content = (base / "app.py").read_text(encoding="utf-8")
            self.assertIn("auto-discovered", app_content)
            self.assertNotIn("app.add_routes", app_content)
            self.assertFalse((base / "schemas").exists())
            self.assertFalse((base / "serializers").exists())
            self.assertTrue((base / "commands").exists())
            self.assertTrue((base / "commands" / "hello.py").exists())
            self.assertFalse((base / "routes" / "home.py").exists())
            self.assertFalse((base / "tasks").exists())
            self.assertFalse((base / "ws").exists())
            self.assertFalse((base / "graphql_schema").exists())
            self.assertFalse((base / "middleware").exists())
            self.assertFalse((base / "models").exists())
            self.assertFalse((base / "setraft.py").exists())
            self.assertFalse((base / "bootstrap.structure.json").exists())
            self.assertFalse((base / "raft_check.py").exists())

            pyproject_content = (base / "pyproject.toml").read_text(encoding="utf-8")
            self.assertNotIn("sqlalchemy", pyproject_content)
            self.assertNotIn("raftsql", pyproject_content)

            app_content = (base / "app.py").read_text(encoding="utf-8")
            self.assertNotIn("raftsql.setup()", app_content)
            self.assertNotIn("@app.route", app_content)
            self.assertIn("OpenAPIRouter", app_content)
            self.assertIn("app.include_router(openapi.router)", app_content)

            # ORM-only artifacts must NOT exist in the minimal scaffold
            self.assertFalse((base / "routes" / "users.py").exists())
            self.assertFalse((base / "models").exists())

    def test_full_bootstrap_includes_selected_feature_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "full_project"
            _scaffold_project(
                base,
                project_name="full_project",
                use_openapi=True,
                use_orm=True,
                use_scheduler=True,
                use_websocket=True,
                use_env=True,
                use_middleware_starter=True,
            )

            self.assertTrue((base / "tasks").exists())
            self.assertTrue((base / "ws").exists())
            self.assertFalse((base / "graphql_schema").exists())
            self.assertTrue((base / "models").exists())
            self.assertFalse((base / "models" / "user.py").exists())
            self.assertTrue((base / "models" / "__init__.py").exists())
            self.assertTrue((base / "setraft.py").exists())
            self.assertTrue((base / "middleware").exists())
            self.assertFalse((base / "bootstrap.structure.json").exists())
            self.assertFalse((base / "raft_check.py").exists())

            pyproject_content = (base / "pyproject.toml").read_text(encoding="utf-8")
            self.assertIn("raftsql", pyproject_content)
            self.assertIn("psycopg2-binary", pyproject_content)
            self.assertIn("asyncpg", pyproject_content)
            self.assertNotIn("sqlalchemy", pyproject_content)

            app_content = (base / "app.py").read_text(encoding="utf-8")
            self.assertIn("raftsql.setup()", app_content)
            self.assertIn("OpenAPIRouter", app_content)
            self.assertNotIn("@app.route", app_content)

            self.assertFalse((base / "routes" / "users.py").exists())
            self.assertFalse((base / "routes" / "home.py").exists())

            models_init = (base / "models" / "__init__.py").read_text(encoding="utf-8")
            self.assertIn("__all__", models_init)


if __name__ == "__main__":
    unittest.main()
