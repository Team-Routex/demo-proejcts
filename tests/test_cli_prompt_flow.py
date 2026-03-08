import unittest
from click.testing import CliRunner

from raft.cli.main import cli


class CliPromptFlowTests(unittest.TestCase):
    def test_celery_prompt_is_skipped_when_scheduler_selected(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            # openapi, graphql, orm, scheduler, middleware, websocket, env
            user_input = "n\nn\nn\ny\nn\nn\nn\n"
            result = runner.invoke(cli, ["init", "skip_celery_project"], input=user_input)

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Skipping Celery prompt", result.output)
        self.assertNotIn("Use task queue (Celery)?", result.output)

    def test_celery_prompt_is_shown_when_scheduler_not_selected(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            # openapi, graphql, orm, scheduler, middleware, celery, websocket, env
            user_input = "n\nn\nn\nn\nn\nn\nn\nn\n"
            result = runner.invoke(cli, ["init", "ask_celery_project"], input=user_input)

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Use task queue (Celery)?", result.output)


if __name__ == "__main__":
    unittest.main()
