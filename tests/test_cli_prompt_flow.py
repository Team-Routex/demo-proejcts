import unittest
from click.testing import CliRunner

from raft.cli.main import cli


class CliPromptFlowTests(unittest.TestCase):
    def test_celery_prompt_is_never_shown(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            # pydantic, openapi, orm, scheduler, middleware, websocket, env
            user_input = "n\nn\nn\nn\nn\nn\nn\n"
            result = runner.invoke(cli, ["init", "no_celery_project"], input=user_input)

        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("Use GraphQL?", result.output)
        self.assertNotIn("Use task queue (Celery)?", result.output)
        self.assertNotIn("Celery", result.output)


if __name__ == "__main__":
    unittest.main()
