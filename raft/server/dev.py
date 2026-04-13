"""
raft.server.dev
~~~~~~~~~~~~~~~

Development server with hot-reload powered by ``watchfiles``.

Usage::

    from raft.server.dev import run_dev_server
    run_dev_server("app:app", host="127.0.0.1", port=8000)

Or via CLI::

    raft runserver --reload
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

from raft.config.settings import settings


def _ensure_uvicorn_worker_import_path(project_root: Path) -> str:
    """Make the project root importable in uvicorn worker processes.

    With ``reload`` or multiple ``workers``, uvicorn starts subprocesses using
    ``multiprocessing`` "spawn" (notably on Windows). A fresh interpreter may
    not place the current working directory on ``sys.path``, while the parent
    process often can still import ``app`` — so ``raft runserver`` appears
    broken even though ``app.py`` exists. Prepending ``PYTHONPATH`` is inherited
    by child processes and matches what ``uvicorn.run(..., app_dir=...)`` does
    for the parent only.
    """
    root = str(project_root.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        parts = [p for p in existing.split(os.pathsep) if p]
        if root not in parts:
            os.environ["PYTHONPATH"] = root + os.pathsep + existing
    else:
        os.environ["PYTHONPATH"] = root
    return root


def run_dev_server(
    app_path: str = "app:app",
    host: str | None = None,
    port: int | None = None,
) -> None:
    """Start a development server with hot-reload.

    Parameters:
        app_path: Import path to the ASGI app, e.g. ``"myapp.main:app"``.
        host: Bind address (default from settings).
        port: Bind port (default from settings).
    """
    root = _ensure_uvicorn_worker_import_path(Path.cwd())
    uvicorn.run(
        app_path,
        host=host or settings.HOST,
        port=port or settings.PORT,
        reload=True,
        reload_dirs=[root],
        log_level=settings.LOG_LEVEL,
        app_dir=root,
    )


def run_prod_server(
    app_path: str = "app:app",
    host: str | None = None,
    port: int | None = None,
    workers: int = 1,
) -> None:
    """Start a production server via uvicorn (no reload).

    Parameters:
        app_path: Import path to the ASGI app.
        host: Bind address.
        port: Bind port.
        workers: Number of worker processes.
    """
    root = _ensure_uvicorn_worker_import_path(Path.cwd())
    uvicorn.run(
        app_path,
        host=host or settings.HOST,
        port=port or settings.PORT,
        reload=False,
        workers=workers,
        log_level=settings.LOG_LEVEL,
        app_dir=root,
    )
