"""
raft.config.settings
~~~~~~~~~~~~~~~~~~~~

Application configuration powered by python-decouple.

Reads from a `.env` file or environment variables.  All settings are typed
and have sensible defaults for development.

Usage::

    from raft.config.settings import settings
    print(settings.DEBUG)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from decouple import config, Csv


class RaftSettings:
    """Central configuration object for a Raft application.

    Attributes:
        DEBUG: Enable debug mode (default True in dev).
        SECRET_KEY: Secret used for session signing and CSRF tokens.
        ALLOWED_HOSTS: Comma-separated list of allowed hostnames.
        CORS_ALLOWED_ORIGINS: Comma-separated origins for CORS.
        SESSION_COOKIE_NAME: Name of the session cookie.
        SESSION_MAX_AGE: Session lifetime in seconds (default 1 hour).
        HOST: Server bind host.
        PORT: Server bind port.
        LOG_LEVEL: Logging level string.
    """

    def __init__(self) -> None:
        self.DEBUG: bool = config("RAFT_DEBUG", default=True, cast=bool)
        self.SECRET_KEY: str = config(
            "RAFT_SECRET_KEY", default="change-me-in-production"
        )
        self.ALLOWED_HOSTS: list[str] = config(
            "RAFT_ALLOWED_HOSTS", default="*", cast=Csv()
        )
        self.CORS_ALLOWED_ORIGINS: list[str] = config(
            "RAFT_CORS_ALLOWED_ORIGINS", default="*", cast=Csv()
        )
        self.CORS_ALLOW_METHODS: list[str] = config(
            "RAFT_CORS_ALLOW_METHODS",
            default="GET,POST,PUT,PATCH,DELETE,OPTIONS",
            cast=Csv(),
        )
        self.CORS_ALLOW_HEADERS: list[str] = config(
            "RAFT_CORS_ALLOW_HEADERS",
            default="Content-Type,Authorization",
            cast=Csv(),
        )
        self.SESSION_COOKIE_NAME: str = config(
            "RAFT_SESSION_COOKIE_NAME", default="raft_session"
        )
        self.SESSION_MAX_AGE: int = config(
            "RAFT_SESSION_MAX_AGE", default=3600, cast=int
        )
        self.HOST: str = config("RAFT_HOST", default="127.0.0.1")
        self.PORT: int = config("RAFT_PORT", default=8000, cast=int)
        self.LOG_LEVEL: str = config("RAFT_LOG_LEVEL", default="info")
        self.OPENAPI_DOCS_VISIBILITY: str = config(
            "RAFT_OPENAPI_DOCS_VISIBILITY", default="public"
        )
        self.OPENAPI_DOCS_PASSWORD: str = config(
            "RAFT_OPENAPI_DOCS_PASSWORD", default=""
        )
        self.AUTO_DISCOVER_MIDDLEWARE: bool = config(
            "RAFT_AUTO_DISCOVER_MIDDLEWARE", default=True, cast=bool
        )
        self.MIDDLEWARE_MODULE_DIR: str = config(
            "RAFT_MIDDLEWARE_DIR", default="middleware"
        )
        self.AUTO_DISCOVER_TASKS: bool = config(
            "RAFT_AUTO_DISCOVER_TASKS", default=True, cast=bool
        )
        self.TASKS_MODULE_DIR: str = config(
            "RAFT_TASKS_DIR", default="tasks"
        )
        self.BASE_DIR: Path = Path.cwd()

    def as_dict(self) -> dict[str, Any]:
        """Return all settings as a dictionary (excludes SECRET_KEY)."""
        return {
            k: v
            for k, v in self.__dict__.items()
            if not k.startswith("_") and k != "SECRET_KEY"
        }


# Module-level singleton — import this everywhere.
settings = RaftSettings()
