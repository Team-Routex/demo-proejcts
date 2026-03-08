import tempfile
import unittest
from pathlib import Path

from raft.cli.main import _scaffold_project


class CliGraphQLScaffoldTests(unittest.TestCase):
    def test_scaffold_with_graphql_creates_graphql_schema_and_deps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "with_graphql"
            _scaffold_project(
                base,
                project_name="with_graphql",
                use_openapi=True,
                api_style="g",
                use_orm=False,
                use_scheduler=False,
                use_celery=False,
                use_websocket=False,
                use_env=True,
                use_middleware_starter=False,
            )

            app_py = (base / "app.py").read_text(encoding="utf-8")
            pyproject = (base / "pyproject.toml").read_text(encoding="utf-8")
            gql_query = base / "graphql_schema" / "query.py"
            readme = (base / "README.md").read_text(encoding="utf-8")

            self.assertTrue(gql_query.exists())
            self.assertIn("GraphQLRouter", app_py)
            self.assertIn('"strawberry-graphql>=0.230.0"', pyproject)
            self.assertIn("API Style: GraphQL", readme)

    def test_scaffold_without_graphql_stays_rest_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "without_graphql"
            _scaffold_project(
                base,
                project_name="without_graphql",
                use_openapi=True,
                api_style="r",
                use_orm=False,
                use_scheduler=False,
                use_celery=False,
                use_websocket=False,
                use_env=True,
                use_middleware_starter=False,
            )

            app_py = (base / "app.py").read_text(encoding="utf-8")
            pyproject = (base / "pyproject.toml").read_text(encoding="utf-8")
            gql_query = base / "graphql_schema" / "query.py"
            readme = (base / "README.md").read_text(encoding="utf-8")

            self.assertFalse(gql_query.exists())
            self.assertNotIn("GraphQLRouter", app_py)
            self.assertNotIn('"strawberry-graphql>=0.230.0"', pyproject)
            self.assertIn("API Style: REST", readme)


if __name__ == "__main__":
    unittest.main()
