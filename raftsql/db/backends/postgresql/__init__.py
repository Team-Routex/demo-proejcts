"""PostgreSQL backend."""
from .backend import PostgreSQLBackend
from ..registry import register_backend

register_backend(PostgreSQLBackend)

__all__ = ["PostgreSQLBackend"]
