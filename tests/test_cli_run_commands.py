"""Tests for raft run project commands."""

from __future__ import annotations

import unittest
from pathlib import Path

import click
from click.testing import CliRunner

from raft.cli.main import cli
from raft.commands.discovery import discover_commands, reset_command_cache


class RunCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_command_cache()

    def tearDown(self) -> None:
        reset_command_cache()

    def test_discover_command_from_folder(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            root = Path("proj")
            cmd_dir = root / "commands"
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "greet.py").write_text(
                'from raft.commands import command\n'
                '@command("greet", help="Say hi")\n'
                'def greet():\n'
                '    print("hi")\n',
                encoding="utf-8",
            )
            found = discover_commands(root=root)
            self.assertIn("greet", found)
            self.assertEqual(found["greet"].help, "Say hi")

    def test_raft_run_invokes_command(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            cmd_dir = Path("commands")
            cmd_dir.mkdir()
            (cmd_dir / "ping.py").write_text(
                'from raft.commands import command\n'
                '@command(help="Ping test")\n'
                'def ping():\n'
                '    print("pong")\n',
                encoding="utf-8",
            )
            reset_command_cache()
            result = runner.invoke(cli, ["run", "ping"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("pong", result.output)

    def test_raft_run_with_click_option(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            cmd_dir = Path("commands")
            cmd_dir.mkdir()
            (cmd_dir / "count.py").write_text(
                "import click\n"
                "from raft.commands import command\n"
                "@command(help='Count')\n"
                "@click.option('--n', default=2, type=int)\n"
                "def count(n):\n"
                "    print(f'count={n}')\n",
                encoding="utf-8",
            )
            reset_command_cache()
            result = runner.invoke(cli, ["run", "count", "--n", "5"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("count=5", result.output)

    def test_raft_run_lists_commands(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            cmd_dir = Path("commands")
            cmd_dir.mkdir()
            (cmd_dir / "alpha.py").write_text(
                'from raft.commands import command\n'
                '@command(help="Alpha cmd")\n'
                'def alpha():\n'
                '    pass\n',
                encoding="utf-8",
            )
            reset_command_cache()
            result = runner.invoke(cli, ["run"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("alpha", result.output)


if __name__ == "__main__":
    unittest.main()
