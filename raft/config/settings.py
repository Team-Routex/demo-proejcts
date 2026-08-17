"""
raft.config.settings
~~~~~~~~~~~~~~~~~~~~

Application configuration powered by python-decouple.

Reads from a ``.env`` file or environment variables.  All settings are typed
and have sensible defaults for development.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from decouple import config, Csv


def _env_bool(name: str, default: bool) -> bool:
    raw = config(name, default="")
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if not text:
        return default
    return text in {"1", "true", "yes", "on"}


class RaftSettings:
    """Central configuration object for a Raft application."""

    def __init__(self) -> None:
        self.DEBUG: bool = config("RAFT_DEBUG", default=True, cast=bool)
        self.SECRET_KEY: str = config(
            "RAFT_SECRET_KEY", default="change-me-in-production"
        )
        if not self.DEBUG and (
            self.SECRET_KEY == "change-me-in-production" or len(self.SECRET_KEY) < 16
        ):
            raise ValueError(
                "Insecure RAFT_SECRET_KEY. You must set RAFT_SECRET_KEY in production."
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

        # Sessions
        self.SESSION_COOKIE_NAME: str = config(
            "RAFT_SESSION_COOKIE_NAME", default="raft_session"
        )
        self.SESSION_MAX_AGE: int = config(
            "RAFT_SESSION_MAX_AGE", default=3600, cast=int
        )
        self.SESSION_BACKEND: str = config(
            "RAFT_SESSION_BACKEND", default="memory"
        ).strip().lower()
        self.SESSION_COOKIE_PATH: str = config(
            "RAFT_SESSION_COOKIE_PATH", default="/"
        )
        self.SESSION_COOKIE_DOMAIN: str = config(
            "RAFT_SESSION_COOKIE_DOMAIN", default=""
        ).strip()
        self.SESSION_COOKIE_SAMESITE: str = config(
            "RAFT_SESSION_COOKIE_SAMESITE", default="Lax"
        ).strip() or "Lax"
        # Secure cookies default on when DEBUG is false
        self.SESSION_COOKIE_SECURE: bool = _env_bool(
            "RAFT_SESSION_COOKIE_SECURE", default=not self.DEBUG
        )
        self.SESSION_COOKIE_HTTPONLY: bool = _env_bool(
            "RAFT_SESSION_COOKIE_HTTPONLY", default=True
        )

        self.REDIS_URL: str = config("RAFT_REDIS_URL", default="")
        self.REDIS_PREFIX: str = config("RAFT_REDIS_PREFIX", default="raft:")

        self.JWT_SECRET: str = config("RAFT_JWT_SECRET", default="")
        self.JWT_ALGORITHM: str = config("RAFT_JWT_ALGORITHM", default="HS256")
        self.JWT_EXPIRE_MINUTES: int = config(
            "RAFT_JWT_EXPIRE_MINUTES", default=60, cast=int
        )

        self.HOST: str = config("RAFT_HOST", default="127.0.0.1")
        self.PORT: int = config("RAFT_PORT", default=8000, cast=int)
        self.LOG_LEVEL: str = config("RAFT_LOG_LEVEL", default="info")

        # OpenAPI / Swagger / ReDoc
        # Enabled by default; set RAFT_OPENAPI_DOCS_ENABLED=false in production
        # to return 404 for /docs, /redoc, and /openapi.json.
        self.OPENAPI_DOCS_ENABLED: bool = _env_bool(
            "RAFT_OPENAPI_DOCS_ENABLED", default=True
        )
        # public | private | disabled (disabled == enabled false)
        self.OPENAPI_DOCS_VISIBILITY: str = config(
            "RAFT_OPENAPI_DOCS_VISIBILITY", default="public"
        ).strip().lower()
        self.OPENAPI_DOCS_USERNAME: str = config(
            "RAFT_OPENAPI_DOCS_USERNAME", default=""
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
        self.COMMANDS_MODULE_DIR: str = config(
            "RAFT_COMMANDS_DIR", default="commands"
        )

        # Rate limiting (opt-in; use reverse proxy limits in high-traffic prod)
        self.RATE_LIMIT_ENABLED: bool = _env_bool(
            "RAFT_RATE_LIMIT_ENABLED", default=False
        )
        self.RATE_LIMIT_REQUESTS: int = config(
            "RAFT_RATE_LIMIT_REQUESTS", default=100, cast=int
        )
        self.RATE_LIMIT_WINDOW_SECONDS: int = config(
            "RAFT_RATE_LIMIT_WINDOW_SECONDS", default=60, cast=int
        )
        self.RATE_LIMIT_BACKEND: str = config(
            "RAFT_RATE_LIMIT_BACKEND", default="memory"
        ).strip().lower()

        self.AUTO_DISCOVER_ROUTES: bool = config(
            "RAFT_AUTO_DISCOVER_ROUTES", default=True, cast=bool
        )
        self.ROUTES_SCAN: str = config(
            "RAFT_ROUTES_SCAN", default="project"
        ).strip().lower()
        self.ROUTES_MODULE_DIR: str = config(
            "RAFT_ROUTES_DIR", default="routes"
        )
        self.BASE_DIR: Path = Path.cwd()

    def as_dict(self) -> dict[str, Any]:
        """Return all settings as a dictionary (excludes secrets)."""
        secret_keys = {"SECRET_KEY", "JWT_SECRET", "OPENAPI_DOCS_PASSWORD"}
        return {
            k: v
            for k, v in self.__dict__.items()
            if not k.startswith("_") and k not in secret_keys
        }


settings = RaftSettings()
