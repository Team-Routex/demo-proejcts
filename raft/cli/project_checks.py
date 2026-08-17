"""
Project health checks for ``raft check`` (CLI-internal; no generated checker file).
"""

from __future__ import annotations

import asyncio
import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

def _read_dotenv_value(root: Path, key: str) -> str:
    """Read *key* from *root*/.env when present (simple KEY=value parser)."""
    path = root / ".env"
    if not path.is_file():
        return ""
    prefix = f"{key}="
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(prefix):
            val = line[len(prefix) :].strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                return val[1:-1]
            return val
    return ""


_KNOWN_PLACEHOLDER_SECRETS = frozenset(
    {
        "",
        "change-me-in-production",
        "change-me-to-a-random-secret",
        "change-me-to-a-long-random-secret",
    }
)


def _mypy_typecheck(root: Path) -> tuple[str, bool, str]:
    """Run Mypy static analysis on project source files."""
    try:
        from mypy import api
    except ImportError:
        return ("Mypy static analysis", True, "N/A (mypy not installed)")

    targets: list[str] = []
    for path in root.glob("*.py"):
        targets.append(str(path))
    for folder in ("routes", "views", "models", "middleware", "tasks", "ws"):
        sub = root / folder
        if sub.is_dir():
            targets.append(str(sub))

    if not targets:
        return ("Mypy static analysis", True, "N/A (no python source targets)")

    args = ["--ignore-missing-imports", "--follow-imports=skip"] + targets
    stdout, stderr, status = api.run(args)
    if status == 0:
        return ("Mypy static analysis", True, "Pass (0 type errors)")
    else:
        first_err = stdout.strip().splitlines()[0] if stdout.strip() else "Type check failed"
        return ("Mypy static analysis", False, first_err)


def _default_asgi_entry_module(root: Path) -> str | None:
    if (root / "app.py").exists():
        return "app"
    if (root / "main.py").exists():
        return "main"
    return None


def _check_default_asgi_importable(mod_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(mod_name)
    except Exception as exc:
        return False, f"Fix errors in {mod_name}.py so it can be imported: {exc}"
    module = sys.modules[mod_name]
    if not hasattr(module, "app"):
        return False, f"Define `app` (e.g. `app = Raft()`) in {mod_name}.py"
    return True, ""


def _build_asyncpg_dsn(db: dict[str, Any]) -> str:
    user = quote_plus(str(db.get("USER", "postgres")))
    password = quote_plus(str(db.get("PASSWORD", "")))
    host = str(db.get("HOST", "localhost"))
    port = int(db.get("PORT", 5432))
    name = quote_plus(str(db.get("NAME", "postgres")))
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


async def _asyncpg_ping(dsn: str, timeout: float) -> None:
    import asyncpg

    conn = await asyncio.wait_for(asyncpg.connect(dsn=dsn), timeout=timeout)
    await conn.close()


def _postgres_tcp_reachable(db: dict[str, Any]) -> tuple[bool, str]:
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        return False, "Install asyncpg to verify PostgreSQL (pip install asyncpg)"

    dsn = _build_asyncpg_dsn(db)
    try:
        asyncio.run(_asyncpg_ping(dsn, timeout=5.0))
    except Exception as exc:
        return False, f"Could not connect: {exc}"
    return True, "Server accepted connection"


def _ws_starter_modules(root: Path) -> list[Path]:
    ws_dir = root / "ws"
    if not ws_dir.is_dir():
        return []
    return sorted(
        p
        for p in ws_dir.glob("*.py")
        if p.name != "__init__.py" and not p.name.startswith("_")
    )


def _pytest_output_tail(text: str, max_len: int = 800) -> str:
    t = text.strip()
    if len(t) <= max_len:
        return t
    return "…" + t[-max_len:]


def _pytest_suite(root: Path) -> tuple[str, bool, str]:
    """Run ``python -m pytest -q`` in *root* (subprocess, clean import path)."""
    try:
        import pytest  # noqa: F401
    except ImportError:
        return (
            "pytest suite",
            True,
            "N/A (pytest not installed — pip install pytest)",
        )

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=line"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return ("pytest suite", False, "pytest exceeded 10 minute timeout")
    except OSError as exc:
        return ("pytest suite", False, f"could not run pytest: {exc}")

    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    if proc.returncode == 0:
        tail = _pytest_output_tail(proc.stdout or "ok")
        return ("pytest suite", True, tail or "all tests passed")
    if proc.returncode == 5:
        return ("pytest suite", True, "no tests collected (add a tests/ package or test_*.py files)")
    return ("pytest suite", False, _pytest_output_tail(out) or f"exit code {proc.returncode}")


def _raft_app_route_summary(mod_name: str) -> tuple[str, bool, str]:
    try:
        module = importlib.import_module(mod_name)
        app_obj = getattr(module, "app", None)
    except Exception as exc:
        return ("Raft route summary", False, f"Could not load app for introspection: {exc}")

    from raft.core.app import Raft

    if not isinstance(app_obj, Raft):
        return ("Raft route summary", True, "app is not a Raft() instance — skipped")

    n_http = len(app_obj.router.routes)
    n_ws = len(app_obj.websocket_router.routes)
    return (
        "Raft route summary",
        True,
        f"{n_http} HTTP route(s), {n_ws} WebSocket route(s)",
    )


def collect_health_checks(
    root: Path | None = None,
    *,
    run_pytest: bool = True,
) -> list[tuple[str, bool, str]]:
    """Return rows ``(label, passed, hint)`` for ``raft check``."""
    root = (root or Path.cwd()).resolve()
    root_s = str(root)
    path_added = False
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
        path_added = True

    checks: list[tuple[str, bool, str]] = []

    try:
        env_exists = (root / ".env").exists()
        checks.append((".env file", env_exists, "Create a .env file with RAFT_SECRET_KEY"))

        app_exists = (root / "app.py").exists() or (root / "main.py").exists()
        checks.append(
            ("App entry point (app.py or main.py)", app_exists, "Create app.py with your Raft() app"),
        )

        mod_name: str | None = None
        if app_exists:
            mod_name = _default_asgi_entry_module(root)
            if mod_name:
                asgi_ok, asgi_hint = _check_default_asgi_importable(mod_name)
                checks.append(
                    ("ASGI app import (module + app)", asgi_ok, asgi_hint or "Import failed"),
                )

        secret_s = (
            _read_dotenv_value(root, "RAFT_SECRET_KEY").strip()
            or os.environ.get("RAFT_SECRET_KEY", "").strip()
        )
        secret_ok = bool(secret_s) and secret_s not in _KNOWN_PLACEHOLDER_SECRETS
        checks.append(
            (
                "RAFT_SECRET_KEY configured",
                secret_ok,
                "Set RAFT_SECRET_KEY in .env to a long random value",
            ),
        )

        dep_ok = True
        missing: list[str] = []
        for mod in ("uvicorn", "pydantic", "decouple", "itsdangerous", "click", "rich"):
            try:
                __import__(mod)
            except ImportError:
                dep_ok = False
                missing.append(mod)
        dep_hint = f"pip install {' '.join(missing)}" if missing else ""
        checks.append(("Core Python dependencies", dep_ok, dep_hint))

        pyproject = (root / "pyproject.toml").exists()
        checks.append(("pyproject.toml", pyproject, "Add pyproject.toml for dependency management"))

        # --- ORM / PostgreSQL / raftsql ------------------------------------
        if (root / "setraft.py").exists():
            try:
                setraft_mod = importlib.import_module("setraft")
                db = getattr(setraft_mod, "DATABASE", None)
                db_ok = isinstance(db, dict) and "ENGINE" in db
                checks.append(
                    (
                        "setraft.DATABASE configuration",
                        db_ok,
                        "Define DATABASE = {..., \"ENGINE\": \"postgresql\", ...} in setraft.py",
                    ),
                )
                if db_ok and isinstance(db, dict):
                    eng = str(db.get("ENGINE", "")).lower()
                    if "postgres" in eng:
                        ok, hint = _postgres_tcp_reachable(db)
                        checks.append(("PostgreSQL server (TCP)", ok, hint))
                    else:
                        checks.append(
                            (
                                "PostgreSQL server (TCP)",
                                True,
                                f"Skipped (ENGINE={db.get('ENGINE')!r} is not PostgreSQL)",
                            ),
                        )
            except Exception as exc:
                checks.append(
                    (
                        "setraft.DATABASE configuration",
                        False,
                        f"setraft.py failed to import: {exc}",
                    ),
                )

            raftsql_ok = False
            try:
                __import__("raftsql")
                raftsql_ok = True
            except ImportError:
                try:
                    __import__("RaftSQL")
                    raftsql_ok = True
                except ImportError:
                    pass
            checks.append(
                (
                    "raftsql package import",
                    raftsql_ok,
                    "Install raftsql when using the ORM",
                ),
            )

        # --- WebSocket ------------------------------------------------------
        ws_files = _ws_starter_modules(root)
        if ws_files:
            try:
                __import__("websockets")
                checks.append(("WebSocket library (websockets)", True, ""))
            except ImportError:
                checks.append(
                    (
                        "WebSocket library (websockets)",
                        False,
                        "Project has ws/*.py — pip install websockets",
                    ),
                )
            chat_py = root / "ws" / "chat.py"
            if chat_py.exists():
                try:
                    importlib.import_module("ws.chat")
                    checks.append(("WebSocket starter (ws.chat)", True, "module imports"))
                except Exception as exc:
                    checks.append(("WebSocket starter (ws.chat)", False, str(exc)))
            else:
                checks.append(
                    (
                        "WebSocket starter (ws/chat.py)",
                        True,
                        "Custom ws modules present — verify imports manually",
                    ),
                )
        else:
            checks.append(("WebSocket starter (ws/)", True, "N/A (no ws/*.py beyond __init__)"))

        # --- Task scheduler -------------------------------------------------
        if (root / "tasks" / "scheduler.py").exists():
            try:
                m = importlib.import_module("tasks.scheduler")
                has_reg = callable(getattr(m, "register_scheduled_tasks", None))
                checks.append(
                    (
                        "Task scheduler hook (tasks.scheduler)",
                        has_reg,
                        "Define register_scheduled_tasks(app) in tasks/scheduler.py",
                    ),
                )
            except Exception as exc:
                checks.append(("Task scheduler hook (tasks.scheduler)", False, str(exc)))
        else:
            checks.append(("Task scheduler hook (tasks/scheduler.py)", True, "N/A"))

        # --- Middleware folder --------------------------------------------
        mw_dir = root / "middleware"
        if mw_dir.is_dir():
            stubs = [
                p for p in mw_dir.glob("*.py") if p.name != "__init__.py" and not p.name.startswith("_")
            ]
            if stubs:
                checks.append(
                    (
                        "Custom middleware (middleware/)",
                        True,
                        f"{len(stubs)} module(s); use *_middleware names for autodiscovery",
                    ),
                )

        # --- Raft route surface -------------------------------------------
        # --- Mypy Static Type Checking ------------------------------------
        checks.append(_mypy_typecheck(root))

    finally:
        if path_added and sys.path and sys.path[0] == root_s:
            sys.path.pop(0)

    if run_pytest:
        checks.append(_pytest_suite(root))

    return checks


