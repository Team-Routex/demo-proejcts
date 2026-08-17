"""
raft.cli.scaffold
~~~~~~~~~~~~~~~~~

Project scaffolding for ``raft init``.
"""

from __future__ import annotations

from pathlib import Path


def scaffold_project(
    base: Path,
    *,
    project_name: str,
    use_pydantic: bool = True,
    use_openapi: bool,
    use_orm: bool,
    use_scheduler: bool,
    use_websocket: bool,
    use_env: bool,
    use_middleware_starter: bool = False,
) -> None:
    """Generate the project directory structure and starter files."""
    dirs = [base, base / "routes", base / "views", base / "commands"]
    if use_pydantic:
        dirs.append(base / "schemas")
    if use_middleware_starter:
        dirs.append(base / "middleware")
    if use_orm:
        dirs.append(base / "models")
    if use_scheduler:
        dirs.append(base / "tasks")
    if use_websocket:
        dirs.append(base / "ws")

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        init = d / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")

    (base / "routes" / "__init__.py").write_text(_ROUTES_INIT_TEMPLATE, encoding="utf-8")
    (base / "commands" / "__init__.py").write_text(_COMMANDS_INIT_TEMPLATE, encoding="utf-8")
    (base / "commands" / "hello.py").write_text(_COMMANDS_HELLO_TEMPLATE, encoding="utf-8")
    if use_pydantic:
        (base / "schemas" / "__init__.py").write_text(_SCHEMAS_INIT_TEMPLATE, encoding="utf-8")
    if use_orm:
        (base / "models" / "__init__.py").write_text(
            _MODELS_INIT_EMPTY_TEMPLATE, encoding="utf-8"
        )

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

    pyproject = f"""[project]
name = "{project_name}"
version = "0.1.0"
description = "A Raft Framework project"
requires-python = ">=3.12"
dependencies = [
    {", ".join(deps)}
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""
    (base / "pyproject.toml").write_text(pyproject, encoding="utf-8")

    if use_env:
        import secrets

        env_secret = secrets.token_urlsafe(48)
        (base / ".env").write_text(
            _ENV_TEMPLATE.format(project_name=project_name, secret_key=env_secret),
            encoding="utf-8",
        )

    if use_orm:
        (base / "setraft.py").write_text(_SETRAFT_TEMPLATE, encoding="utf-8")

    (base / "app.py").write_text(
        _REST_APP_TEMPLATE.format(
            project_name=project_name,
            orm_import=("import raftsql\n" if use_orm else ""),
            orm_setup=("raftsql.setup()\n" if use_orm else ""),
            openapi_import=(
                "from raft.openapi import OpenAPIRouter\n" if use_openapi else ""
            ),
            openapi_setup=(
                "\n# OpenAPI / Swagger / ReDoc — disable or password-protect via .env\n"
                f'openapi = OpenAPIRouter(app, title="{project_name} API")\n'
                "app.include_router(openapi.router)\n"
                if use_openapi
                else ""
            ),
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
        ),
        encoding="utf-8",
    )

    (base / "README.md").write_text(
        _SCAFFOLD_README_TEMPLATE.format(
            project_name=project_name,
            pydantic_enabled=("Yes" if use_pydantic else "No"),
            openapi_enabled=("Yes" if use_openapi else "No"),
            scheduler_enabled=("Yes" if use_scheduler else "No"),
            middleware_starter_enabled=("Yes" if use_middleware_starter else "No"),
            orm_enabled=("Yes" if use_orm else "No"),
            websocket_enabled=("Yes" if use_websocket else "No"),
            env_enabled=("Yes" if use_env else "No"),
        ),
        encoding="utf-8",
    )

    if use_scheduler:
        (base / "tasks" / "scheduler.py").write_text(
            _TASK_SCHEDULER_TEMPLATE, encoding="utf-8"
        )
        (base / "tasks" / "periodic.py").write_text(
            _TASKS_AUTODISCOVERY_TEMPLATE, encoding="utf-8"
        )

    if use_websocket:
        (base / "ws" / "chat.py").write_text(_WS_CHAT_TEMPLATE, encoding="utf-8")

    if use_middleware_starter:
        (base / "middleware" / "request_id.py").write_text(
            _MIDDLEWARE_STARTER_TEMPLATE, encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_ENV_TEMPLATE = """# Raft Framework Configuration
RAFT_DEBUG=true
RAFT_SECRET_KEY={secret_key}
RAFT_HOST=127.0.0.1
RAFT_PORT=8000
RAFT_ALLOWED_HOSTS=*
RAFT_CORS_ALLOWED_ORIGINS=*
RAFT_LOG_LEVEL=info
RAFT_SESSION_BACKEND=memory
RAFT_OPENAPI_DOCS_ENABLED=true
RAFT_OPENAPI_DOCS_VISIBILITY=public
# RAFT_OPENAPI_DOCS_USERNAME=docs
# RAFT_OPENAPI_DOCS_PASSWORD=change-me
# RAFT_REDIS_URL=redis://localhost:6379/0
# RAFT_REDIS_PREFIX=raft:
# RAFT_JWT_SECRET=
RAFT_JWT_ALGORITHM=HS256
RAFT_JWT_EXPIRE_MINUTES=60
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME={project_name}
"""

_REST_APP_TEMPLATE = '''"""
{project_name} — Main application entry point.
"""

from raft import Raft
{orm_import}
{openapi_import}
{scheduler_import}
{websocket_import}

# HTTP routes are auto-discovered anywhere in the project (not only ``routes/``).
# Export ``routes = [route(...), ...]`` or ``router = Router(...)`` in any module.
{orm_setup}
app = Raft()
{openapi_setup}
{scheduler_setup}
{websocket_setup}
'''

_ROUTES_INIT_TEMPLATE = '''"""Optional ``routes/`` package (not required).

Raft discovers hybrid route definitions **anywhere** under the project root:

- ``routes = [route("/path/", view, methods=["GET"]), ...]``
- ``router = Router(...)`` with ``@router.get`` / ``@router.post``

Put modules here, under ``api/``, ``views/``, or any other package — as long as
they export ``routes`` or ``router``, they are auto-loaded when ``app = Raft()``
starts. No ``app.add_routes()`` call is needed.

Example ``api/users.py``::

    from raft import route, Response

    async def list_users(request):
        return Response.success(data=[])

    routes = [
        route("/users/", list_users, methods=["GET"]),
    ]
"""

__all__: list[str] = []
'''

_COMMANDS_INIT_TEMPLATE = '''"""Project management commands — run with ``raft run <name>``.

Add one module per command under this folder. Example::

    # commands/seed.py
    from raft.commands import command

    @command(help="Seed demo data")
    def seed():
        print("Seeding...")
"""

__all__: list[str] = []
'''

_COMMANDS_HELLO_TEMPLATE = '''"""Example project command — ``raft run hello``."""

from raft.commands import command


@command(help="Print a greeting from your project")
def hello():
    print("Hello from your Raft project command!")
'''

_SCHEMAS_INIT_TEMPLATE = '''"""Pydantic schemas & data models — ``pydantic.BaseModel``.

Example ``schemas/user.py``::

    from pydantic import BaseModel, EmailStr

    class UserSchema(BaseModel):
        username: str
        email: EmailStr
"""

__all__: list[str] = []
'''

_MODELS_INIT_EMPTY_TEMPLATE = '''"""ORM models — RaftSQL ``Model`` subclasses.

Run ``raftsql generate`` and ``raftsql apply`` after configuring ``setraft.py``.
"""

__all__: list[str] = []
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

- Pydantic Validation & Schemas: {pydantic_enabled}
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

- Main app file: `app.py` — just `app = Raft()`; routes auto-discover project-wide.
- Define handlers in any module with either:
  - `routes = [route("/path/", view, methods=["GET"]), ...]`, or
  - `router = Router(...)` with `@router.get` / `@router.post`
- No `app.add_routes(...)` needed — optional `routes/` folder is only a convention.
'''
