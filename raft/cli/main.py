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

import importlib
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


def _normalize_app_path(app_path: str) -> str:
    """Normalize CLI app path into uvicorn's ``module:attribute`` format."""
    path = app_path.strip()
    if not path:
        return "app:app"
    if ":" not in path:
        return f"{path}:app"
    return path


def _default_asgi_entry_module() -> str | None:
    """Module name used by default for ``app:app`` / ``main:app`` style projects."""
    if Path("app.py").exists():
        return "app"
    if Path("main.py").exists():
        return "main"
    return None


def _check_default_asgi_importable() -> tuple[bool, str]:
    """Ensure the default entry module imports and exposes ``app`` (like uvicorn)."""
    mod_name = _default_asgi_entry_module()
    if mod_name is None:
        return True, ""
    try:
        module = importlib.import_module(mod_name)
    except Exception as exc:
        return False, f"Fix errors in {mod_name}.py so it can be imported: {exc}"
    if not hasattr(module, "app"):
        return False, f"Define `app` (e.g. `app = Raft()`) in {mod_name}.py"
    return True, ""


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
    use_openapi = click.confirm("  Enable OpenAPI / Docs?", default=False)
    use_graphql = click.confirm("  Use GraphQL?", default=False)
    api_style = "g" if use_graphql else "r"
    use_orm = click.confirm("  Use ORM (RaftSql)?", default=False)
    use_scheduler = click.confirm(
        "  Use built-in Task Scheduler (auto-detect tasks folder)?",
        default=False,
    )
    use_middleware_starter = click.confirm(
        "  Create custom middleware starter file?", default=False
    )
    use_websocket = click.confirm("  Use WebSocket?", default=False)
    use_env = click.confirm("  Use .env file?", default=False)

    # Build project
    base = Path.cwd() / project_name
    _scaffold_project(
        base,
        project_name=project_name,
        use_openapi=use_openapi,
        api_style=api_style,
        use_orm=use_orm,
        use_scheduler=use_scheduler,
        use_websocket=use_websocket,
        use_env=use_env,
        use_middleware_starter=use_middleware_starter,
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

    normalized_app_path = _normalize_app_path(app_path)

    if reload:
        console.print("[cyan]Starting Raft dev server (hot-reload)…[/cyan]")
        run_dev_server(app_path=normalized_app_path, host=host, port=port)
    else:
        console.print("[cyan]Starting Raft production server…[/cyan]")
        run_prod_server(app_path=normalized_app_path, host=host, port=port, workers=workers)


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

    # 2b. default ASGI import (catches broken app.py; complements file-exists check)
    if app_exists:
        asgi_ok, asgi_hint = _check_default_asgi_importable()
        checks.append(
            ("ASGI app import (default app:app)", asgi_ok, asgi_hint or "Import failed"),
        )

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
    dep_hint = f"Install missing: {', '.join(missing)}" if missing else ""
    checks.append(("Core dependencies", dep_ok, dep_hint))

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
    use_scheduler: bool,
    use_websocket: bool,
    use_env: bool,
    use_middleware_starter: bool = False,
) -> None:
    """Generate the project directory structure and starter files."""
    dirs = [
        base,
        base / "routes",
        base / "views",
        base / "serializers",
    ]
    if use_middleware_starter:
        dirs.append(base / "middleware")
    if use_orm:
        dirs.append(base / "models")
    if use_scheduler:
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
            init.write_text("", encoding="utf-8")

    # pyproject.toml
    deps = [
        '"raft-framework>=0.1.0"',
        '"uvicorn[standard]>=0.30.0"',
        '"pydantic>=2.0"',
        '"python-decouple>=3.8"',
    ]
    if use_orm:
        deps.extend(
            [
                '"raftsql>=1.0.0"',
                '"psycopg2-binary>=2.9.0"',
                '"asyncpg>=0.29.0"',
                '"python-dotenv>=1.0.0"',
            ]
        )
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
    (base / "pyproject.toml").write_text(pyproject, encoding="utf-8")

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
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME={project_name}
"""
        (base / ".env").write_text(env_content.format(project_name=project_name), encoding="utf-8")

    # setraft.py (RaftSQL settings)
    if use_orm:
        (base / "setraft.py").write_text(_SETRAFT_TEMPLATE, encoding="utf-8")

    # app.py — main entry point
    if api_style == "g":
        app_code = _GRAPHQL_APP_TEMPLATE.format(
            project_name=project_name,
            orm_import=("import raftsql\n" if use_orm else ""),
            orm_setup=("raftsql.setup()\n" if use_orm else ""),
            scheduler_import=(
                "from tasks.scheduler import register_scheduled_tasks\n"
                if use_scheduler
                else ""
            ),
            scheduler_setup=(
                "\n# Register optional periodic jobs\nregister_scheduled_tasks(app)\n"
                if use_scheduler
                else ""
            ),
            websocket_import=(
                "from ws.chat import register_websocket_routes\n"
                if use_websocket
                else ""
            ),
            websocket_setup=(
                "\n# Register optional websocket routes\nregister_websocket_routes(app)\n"
                if use_websocket
                else ""
            ),
        )
    else:
        app_code = _REST_APP_TEMPLATE.format(
            project_name=project_name,
            orm_import=("import raftsql\n" if use_orm else ""),
            orm_setup=("raftsql.setup()\n" if use_orm else ""),
            scheduler_import=(
                "from tasks.scheduler import register_scheduled_tasks\n"
                if use_scheduler
                else ""
            ),
            scheduler_setup=(
                "\n# Register optional periodic jobs\nregister_scheduled_tasks(app)\n"
                if use_scheduler
                else ""
            ),
            websocket_import=(
                "from ws.chat import register_websocket_routes\n"
                if use_websocket
                else ""
            ),
            websocket_setup=(
                "\n# Register optional websocket routes\nregister_websocket_routes(app)\n"
                if use_websocket
                else ""
            ),
        )
    (base / "app.py").write_text(app_code, encoding="utf-8")

    # routes/home.py
    (base / "routes" / "home.py").write_text(_HOME_ROUTE_TEMPLATE, encoding="utf-8")

    # serializers/user.py — request validation via Raft Serializer (Pydantic-based)
    (base / "serializers" / "user.py").write_text(_USER_SERIALIZER_TEMPLATE, encoding="utf-8")
    (base / "serializers" / "__init__.py").write_text(_SERIALIZERS_INIT_TEMPLATE, encoding="utf-8")

    if use_orm:
        (base / "models" / "user.py").write_text(_USER_MODEL_TEMPLATE, encoding="utf-8")
        (base / "models" / "__init__.py").write_text(_MODELS_INIT_TEMPLATE, encoding="utf-8")

    # Checker file
    (base / "raft_check.py").write_text(_CHECKER_TEMPLATE, encoding="utf-8")

    # Generated README
    generated_readme = _SCAFFOLD_README_TEMPLATE.format(
        project_name=project_name,
        api_style=("GraphQL" if api_style == "g" else "REST"),
        openapi_enabled=("Yes" if use_openapi else "No"),
        scheduler_enabled=("Yes" if use_scheduler else "No"),
        middleware_starter_enabled=("Yes" if use_middleware_starter else "No"),
        orm_enabled=("Yes" if use_orm else "No"),
        websocket_enabled=("Yes" if use_websocket else "No"),
        env_enabled=("Yes" if use_env else "No"),
    )
    (base / "README.md").write_text(generated_readme, encoding="utf-8")

    if api_style == "g":
        (base / "graphql_schema" / "query.py").write_text(
            _GRAPHQL_QUERY_TEMPLATE,
            encoding="utf-8",
        )

    if use_scheduler:
        (base / "tasks" / "scheduler.py").write_text(
            _TASK_SCHEDULER_TEMPLATE,
            encoding="utf-8",
        )
        (base / "tasks" / "periodic.py").write_text(
            _TASKS_AUTODISCOVERY_TEMPLATE,
            encoding="utf-8",
        )

    if use_websocket:
        (base / "ws" / "chat.py").write_text(_WS_CHAT_TEMPLATE, encoding="utf-8")

    if use_middleware_starter:
        (base / "middleware" / "request_id.py").write_text(
            _MIDDLEWARE_STARTER_TEMPLATE,
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_REST_APP_TEMPLATE = '''"""
{project_name} — Main application entry point.
"""

from raft import Raft, RaftResponse
{orm_import}
{scheduler_import}
{websocket_import}

# Routers under ``routes/`` (each module's ``router``) are auto-included.
{orm_setup}
app = Raft()
{scheduler_setup}
{websocket_setup}


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
{orm_import}
{scheduler_import}
{websocket_import}

# REST routers under ``routes/`` are auto-included; GraphQL is mounted below.
{orm_setup}
app = Raft()
{scheduler_setup}
{websocket_setup}

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

_USER_SERIALIZER_TEMPLATE = '''"""User request serializers."""

from raft import Serializer
from raft.serialization import CharField, EmailField, IntegerField


class CreateUserSerializer(Serializer):
    """Inbound body for creating a user."""

    name: str = CharField()
    email: str = EmailField()
    age: int | None = IntegerField(default=None)


class UpdateUserSerializer(Serializer):
    """Inbound body for partial user updates."""

    name: str | None = CharField(default=None)
    email: str | None = EmailField(default=None)
    age: int | None = IntegerField(default=None)
'''

_SERIALIZERS_INIT_TEMPLATE = '''from .user import CreateUserSerializer, UpdateUserSerializer

__all__ = ["CreateUserSerializer", "UpdateUserSerializer"]
'''

_SETRAFT_TEMPLATE = '''"""RaftSQL project configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE = {
    "ENGINE": "postgresql",
    "HOST": os.getenv("DB_HOST", "localhost"),
    "PORT": int(os.getenv("DB_PORT", 5432)),
    "USER": os.getenv("DB_USER", "postgres"),
    "PASSWORD": os.getenv("DB_PASSWORD", ""),
    "NAME": os.getenv("DB_NAME", "postgres"),
}
'''

_USER_MODEL_TEMPLATE = '''"""ORM model examples."""

from raftsql import models


class User(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)

    class Meta:
        db_table = "users"
'''

_MODELS_INIT_TEMPLATE = '''from .user import User

__all__ = ["User"]
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

_TASK_SCHEDULER_TEMPLATE = '''"""Optional scheduled jobs for your Raft app."""


def register_scheduled_tasks(app) -> None:
    """Attach periodic jobs only when this module is included at scaffold time."""

    @app.task(every=60, repeat=True, run_immediately=False)
    async def heartbeat_job() -> None:
        # Replace with real background work.
        print("[scheduler] heartbeat job executed")
'''

_TASKS_AUTODISCOVERY_TEMPLATE = '''"""Autodiscovered tasks.

Any callable tagged with @periodic_task in this folder is auto-loaded by Raft.
You can also import plain functions from this module inside your views.
"""

from raft.tasks import periodic_task


@periodic_task(every=60, repeat=True, run_immediately=False)
async def cleanup_task() -> None:
    print("[tasks] cleanup_task executed")


def build_welcome_message(username: str) -> str:
    """Example plain helper importable in views without scheduling."""
    return f"Welcome, {username}!"
'''

_WS_CHAT_TEMPLATE = '''"""Optional websocket routes for your Raft app."""


def register_websocket_routes(app) -> None:
    """Attach websocket handlers only when this module is scaffolded."""

    @app.websocket("/ws/chat/{room}")
    async def room_chat(ws) -> None:
        room = ws.path_params.get("room", "general")
        await ws.join_room(room)
        await ws.send_json({"event": "joined", "room": room})

        while True:
            try:
                text = await ws.receive_text()
            except ConnectionError:
                break
            await ws.send_room(room, text)
'''

_MIDDLEWARE_STARTER_TEMPLATE = '''"""Custom middleware starter example.

Raft auto-discovers async callables ending with `_middleware` from the
project-level `middleware/` folder.
"""


async def request_id_middleware(request, call_next):
    """Attach an X-Request-ID header to each response."""
    import secrets

    request_id = secrets.token_hex(8)
    request.state["request_id"] = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
'''

_SCAFFOLD_README_TEMPLATE = '''# {project_name}

Generated by `raft init`.

## Enabled Modules

- API Style: {api_style}
- OpenAPI / Docs: {openapi_enabled}
- Built-in Task Scheduler: {scheduler_enabled}
- Custom Middleware Starter: {middleware_starter_enabled}
- ORM (RaftSql): {orm_enabled}
- WebSocket: {websocket_enabled}
- .env File: {env_enabled}

## Quick Start

```bash
uv sync
raft runserver
```

## App Entry

- Main app file: `app.py`
- Add `routes/your_module.py` with a module-level
  `router = Router(...)` to register URLs (auto-discovered).
- Health route example: `GET /home/health`
'''
