"""
raft.cli.main
~~~~~~~~~~~~~

CLI entry point for the ``raft`` command.

Commands:
    raft              — Brand banner + help
    raft init         — Scaffold a new project
    raft run          — Project management commands (commands/)
    raft runserver    — Start the ASGI server
    raft check        — Health checks (+ pytest)
    raft version      — Show version
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from raft.cli import ui
from raft.cli.run_group import register_run_command
from raft.cli.scaffold import scaffold_project

# Back-compat for tests that import the private name
_scaffold_project = scaffold_project


def _normalize_app_path(app_path: str) -> str:
    """Normalize CLI app path into uvicorn's ``module:attribute`` format."""
    path = app_path.strip()
    if not path:
        return "app:app"
    if ":" not in path:
        return f"{path}:app"
    return path


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Raft Framework — ASGI web framework CLI."""
    if ctx.invoked_subcommand is None:
        ui.print_brand(subtitle="ASGI web framework · init · run · runserver · check")
        click.echo(ctx.get_help())


register_run_command(cli)


@cli.command()
@click.argument("project_name", default="myraft")
def init(project_name: str) -> None:
    """Scaffold a new Raft project interactively."""
    ui.print_command_header(
        "New project setup",
        detail=f"Project name: {project_name}",
    )

    features = ui.prompt_features()
    ui.print_feature_summary(features)
    flags = ui.features_to_flags(features)

    base = Path.cwd() / project_name
    if base.exists() and any(base.iterdir()):
        ui.print_error(f"Directory already exists and is not empty: {base}")
        sys.exit(1)

    scaffold_project(base, project_name=project_name, **flags)

    ui.print_success(f"Project [bold]{project_name}[/bold] created at {base}")
    ui.print_next_steps(project_name)


@cli.command()
@click.option("--host", default=None, help="Bind host.")
@click.option("--port", default=None, type=int, help="Bind port.")
@click.option("--reload/--no-reload", default=True, help="Enable hot-reload.")
@click.option("--workers", default=1, type=int, help="Worker count (prod).")
@click.option("--app", "app_path", default="app:app", help="ASGI app import path.")
def runserver(
    host: str | None,
    port: int | None,
    reload: bool,
    workers: int,
    app_path: str,
) -> None:
    """Start the development or production server."""
    from raft.config.settings import settings
    from raft.server.dev import run_dev_server, run_prod_server

    normalized = _normalize_app_path(app_path)
    bind_host = host or settings.HOST
    bind_port = port if port is not None else settings.PORT
    mode = "Development (hot-reload)" if reload else "Production"

    ui.print_server_banner(
        mode=mode,
        app_path=normalized,
        host=bind_host,
        port=bind_port,
    )

    if reload:
        run_dev_server(app_path=normalized, host=host, port=port)
    else:
        run_prod_server(app_path=normalized, host=host, port=port, workers=workers)


@cli.command()
@click.option(
    "--no-tests",
    is_flag=True,
    help="Skip running pytest (otherwise: python -m pytest -q --tb=line).",
)
def check(no_tests: bool) -> None:
    """Verify project health and configuration."""
    from raft.cli.project_checks import collect_health_checks

    ui.print_command_header("Project health check", detail=str(Path.cwd()))
    checks = collect_health_checks(Path.cwd(), run_pytest=not no_tests)
    ok = ui.print_check_results(checks)
    if not ok:
        sys.exit(1)


@cli.command()
def version() -> None:
    """Show the installed Raft Framework version."""
    from raft import __version__

    ui.print_brand()
    ui.console.print(f"  raft-framework [bold cyan]{__version__}[/bold cyan]")


if __name__ == "__main__":
    cli()
