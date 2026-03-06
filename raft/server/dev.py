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

import uvicorn

from raft.config.settings import settings


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
    uvicorn.run(
        app_path,
        host=host or settings.HOST,
        port=port or settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL,
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
    uvicorn.run(
        app_path,
        host=host or settings.HOST,
        port=port or settings.PORT,
        reload=False,
        workers=workers,
        log_level=settings.LOG_LEVEL,
    )
