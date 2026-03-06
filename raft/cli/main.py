"""
raft.cli.main
~~~~~~~~~~~~~

CLI entry point for the ``raft`` command.

Commands:
    raft init           — Scaffold a new Raft project interactively.
    raft runserver      — Start the development server.
    raft check          — Verify project configuration.

Built with Click + Rich for a clean terminal experience.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.group()
def cli() -> None:
    """Raft Framework CLI — project scaffolding and management."""


# ---------------------------------------------------------------------------
# raft init
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("project_name", default="myraft")
def init(project_name: str) -> None:
    """Scaffold a new Raft project interactively."""
    console.print(
        Panel.fit(
            f"[bold cyan]Raft Framework[/bold cyan] — New Project Setup\n"
            f"Project: [bold]{project_name}[/bold]",
            border_style="cyan",
        )
    )

    # Interactive prompts
    use_openapi = click.confirm("  Enable OpenAPI / Docs?", default=True)
    api_style = click.prompt(
        "  API style — (r)est / (g)raphql",
        type=click.Choice(["r", "g"], case_sensitive=False),
        default="r",
    )
    use_orm = click.confirm("  Use ORM (RaftSql)?", default=False)
    use_celery = click.confirm("  Use task queue (Celery)?", default=False)
    use_websocket = click.confirm("  Use WebSocket?", default=False)
    use_env = click.confirm("  Use .env file?", default=True)

    # Build project
    base = Path.cwd() / project_name
    _scaffold_project(
        base,
        project_name=project_name,
        use_openapi=use_openapi,
        api_style=api_style,
        use_orm=use_orm,
        use_celery=use_celery,
        use_websocket=use_websocket,
        use_env=use_env,
    )

    console.print(f"\n[green]✔[/green] Project [bold]{project_name}[/bold] created at {base}")
    console.print(f"  cd {project_name}")
    console.print("  uv sync              # install deps")
    console.print("  raft runserver       # start dev server")


# ---------------------------------------------------------------------------
# raft runserver
# ---------------------------------------------------------------------------

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
    from raft.server.dev import run_dev_server, run_prod_server

    if reload:
        console.print("[cyan]Starting Raft dev server (hot-reload)…[/cyan]")
        run_dev_server(app_path=app_path, host=host, port=port)
    else:
        console.print("[cyan]Starting Raft production server…[/cyan]")
        run_prod_server(app_path=app_path, host=host, port=port, workers=workers)


# ---------------------------------------------------------------------------
# raft check
# ---------------------------------------------------------------------------

@cli.command()
def check() -> None:
    """Verify project health and configuration."""
    console.print(Panel.fit("[bold]Raft Config Checker[/bold]", border_style="yellow"))

    checks: list[tuple[str, bool, str]] = []

    # 1. .env file
    env_exists = Path(".env").exists()
    checks.append((".env file", env_exists, "Create a .env file with RAFT_SECRET_KEY"))

    # 2. app.py / main entry
    app_exists = Path("app.py").exists() or Path("main.py").exists()
    checks.append(("App entry point (app.py)", app_exists, "Create app.py with your Raft() app"))

    # 3. Secret key
    from decouple import config as decouple_config
    secret = decouple_config("RAFT_SECRET_KEY", default="change-me-in-production")
    secret_ok = secret != "change-me-in-production"
    checks.append(("SECRET_KEY is set", secret_ok, "Set RAFT_SECRET_KEY in .env"))

    # 4. Dependencies importable
    dep_ok = True
    missing: list[str] = []
    for mod in ["uvicorn", "pydantic", "decouple", "itsdangerous", "click", "rich"]:
        try:
            __import__(mod)
        except ImportError:
            dep_ok = False
            missing.append(mod)
    checks.append(("Core dependencies", dep_ok, f"Install missing: {', '.join(missing)}" if missing else ""))

    # 5. pyproject.toml
    pyproject = Path("pyproject.toml").exists()
    checks.append(("pyproject.toml", pyproject, "Add a pyproject.toml for dependency management"))

    # Print results
    all_ok = True
    for label, ok, hint in checks:
        icon = "[green]✔[/green]" if ok else "[red]✘[/red]"
        console.print(f"  {icon} {label}")
        if not ok:
            all_ok = False
            if hint:
                console.print(f"      [dim]{hint}[/dim]")

    if all_ok:
        console.print("\n[green bold]All checks passed![/green bold]")
    else:
        console.print("\n[yellow]Some checks failed — see hints above.[/yellow]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Scaffolding helpers
# ---------------------------------------------------------------------------

def _scaffold_project(
    base: Path,
    *,
    project_name: str,
    use_openapi: bool,
    api_style: str,
    use_orm: bool,
    use_celery: bool,
    use_websocket: bool,
    use_env: bool,
) -> None:
    """Generate the project directory structure and starter files."""
    dirs = [
        base,
        base / "routes",
        base / "views",
        base / "middleware",
        base / "schemas",
    ]
    if use_orm:
        dirs.append(base / "models")
    if use_celery:
        dirs.append(base / "tasks")
    if use_websocket:
        dirs.append(base / "ws")
    if api_style == "g":
        dirs.append(base / "graphql_schema")

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # __init__.py files
    for d in dirs:
        init = d / "__init__.py"
        if not init.exists():
            init.write_text("")

    # pyproject.toml
    deps = [
        '"raft-framework>=0.1.0"',
        '"uvicorn[standard]>=0.30.0"',
        '"pydantic>=2.0"',
        '"python-decouple>=3.8"',
    ]
    if use_orm:
        deps.append('"sqlalchemy>=2.0"')
    if use_celery:
        deps.append('"celery>=5.3"')
    if use_websocket:
        deps.append('"websockets>=12.0"')
    if api_style == "g":
        deps.append('"strawberry-graphql>=0.230.0"')

    pyproject = f"""[project]
name = "{project_name}"
version = "0.1.0"
description = "A Raft Framework project"
requires-python = ">=3.12"
dependencies = [
    {', '.join(deps)}
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""
    (base / "pyproject.toml").write_text(pyproject)

    # .env
    if use_env:
        env_content = """# Raft Framework Configuration
RAFT_DEBUG=true
RAFT_SECRET_KEY=change-me-to-a-random-secret
RAFT_HOST=127.0.0.1
RAFT_PORT=8000
RAFT_ALLOWED_HOSTS=*
RAFT_CORS_ALLOWED_ORIGINS=*
RAFT_LOG_LEVEL=info
"""
        (base / ".env").write_text(env_content)

    # app.py — main entry point
    if api_style == "g":
        app_code = _GRAPHQL_APP_TEMPLATE.format(project_name=project_name)
    else:
        app_code = _REST_APP_TEMPLATE.format(project_name=project_name)
    (base / "app.py").write_text(app_code)

    # routes/home.py
    (base / "routes" / "home.py").write_text(_HOME_ROUTE_TEMPLATE)

    # schemas/user.py
    (base / "schemas" / "user.py").write_text(_USER_SCHEMA_TEMPLATE)

    # Checker file
    (base / "raft_check.py").write_text(_CHECKER_TEMPLATE)

    if api_style == "g":
        (base / "graphql_schema" / "query.py").write_text(_GRAPHQL_QUERY_TEMPLATE)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_REST_APP_TEMPLATE = '''"""
{project_name} — Main application entry point.
"""

from raft import Raft, RaftResponse
from routes.home import router as home_router

app = Raft()

# Register route modules
app.include_router(home_router)


@app.route("/", methods=["GET"])
async def index(request):
    return RaftResponse.ok(
        message="Welcome to {project_name}!",
        data={{"version": "0.1.0"}},
    )
'''

_GRAPHQL_APP_TEMPLATE = '''"""
{project_name} — Main application entry point (GraphQL).
"""

import strawberry
from raft import Raft, RaftResponse
from raft.graphql.integration import GraphQLRouter
from graphql_schema.query import Query

app = Raft()

schema = strawberry.Schema(Query)
graphql = GraphQLRouter(schema, path="/graphql")
app.include_router(graphql.router)


@app.route("/", methods=["GET"])
async def index(request):
    return RaftResponse.ok(
        message="Welcome to {project_name}! Visit /graphql",
        data={{"version": "0.1.0"}},
    )
'''

_HOME_ROUTE_TEMPLATE = '''"""Home routes."""

from raft import RaftResponse, Router

router = Router(prefix="/home")


@router.route("/", methods=["GET"])
async def home(request):
    return RaftResponse.ok(message="Home page")


@router.route("/health", methods=["GET"])
async def health(request):
    return RaftResponse.ok(message="OK", data={"healthy": True})
'''

_USER_SCHEMA_TEMPLATE = '''"""User validation schemas."""

from pydantic import BaseModel, EmailStr


class CreateUserSchema(BaseModel):
    """Schema for creating a new user."""
    name: str
    email: str  # Use EmailStr if email-validator is installed.
    age: int | None = None


class UpdateUserSchema(BaseModel):
    """Schema for updating user fields."""
    name: str | None = None
    email: str | None = None
    age: int | None = None
'''

_CHECKER_TEMPLATE = '''"""
Raft project checker — run this file to verify configuration.

    python raft_check.py
"""

import sys
from pathlib import Path


def check() -> bool:
    ok = True
    checks = [
        (".env exists", Path(".env").exists()),
        ("app.py exists", Path("app.py").exists()),
        ("pyproject.toml exists", Path("pyproject.toml").exists()),
    ]
    for label, passed in checks:
        icon = "✔" if passed else "✘"
        print(f"  {icon} {label}")
        if not passed:
            ok = False
    return ok


if __name__ == "__main__":
    print("Raft Project Health Check")
    print("=" * 30)
    if check():
        print("\\nAll checks passed!")
    else:
        print("\\nSome checks failed.")
        sys.exit(1)
'''

_GRAPHQL_QUERY_TEMPLATE = '''"""Root GraphQL query."""

import strawberry


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello from Raft GraphQL!"

    @strawberry.field
    def version(self) -> str:
        return "0.1.0"
'''
