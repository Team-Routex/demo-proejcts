"""
raft.cli.run_group
~~~~~~~~~~~~~~~~~~

``raft run <command>`` — execute project scripts from ``commands/``.
"""

from __future__ import annotations

from pathlib import Path

import click

from raft.cli import ui
from raft.commands.discovery import discover_commands, list_command_names


class ProjectCommandGroup(click.Group):
    """Click group that loads commands from the project's ``commands/`` folder."""

    @staticmethod
    def _project_root() -> Path:
        return Path.cwd()

    def list_commands(self, ctx: click.Context) -> list[str]:
        return list_command_names(root=self._project_root())

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        commands = discover_commands(root=self._project_root())
        return commands.get(cmd_name)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        names = self.list_commands(ctx)
        if not names:
            formatter.write_paragraph()
            formatter.write_text(
                "No project commands found. Add modules under commands/ "
                "and use @command from raft.commands."
            )
            return
        super().format_commands(ctx, formatter)


@click.group(
    cls=ProjectCommandGroup,
    invoke_without_command=True,
    help="Run project management commands from commands/.",
)
@click.pass_context
def run_group(ctx: click.Context) -> None:
    """Run scripts from your project's ``commands/`` folder."""
    if ctx.invoked_subcommand is None:
        project_root = Path.cwd()
        ui.print_command_header("Project commands", detail=str(project_root))
        names = list_command_names(root=project_root)
        if not names:
            ui.print_hint("Create commands/hello.py with @command to get started.")
            ui.console.print()
            click.echo(ctx.get_help())
            return
        commands = discover_commands(root=project_root)
        table_rows = [(name, commands.get(name, click.Command(name)).help or "") for name in names]
        from rich.table import Table

        table = Table(title="Available commands", header_style="bold cyan")
        table.add_column("Command")
        table.add_column("Help", style="bright_black")
        for name, help_text in table_rows:
            table.add_row(name, help_text)
        ui.console.print(table)
        ui.console.print()
        ui.print_hint("Usage: raft run <command> [options]")


def register_run_command(cli: click.Group) -> None:
    """Attach ``run`` to the root CLI group."""
    cli.add_command(run_group, name="run")
