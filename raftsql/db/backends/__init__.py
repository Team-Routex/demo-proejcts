"""
Database backends. Each backend provides quoting, optional features, and connection classes.
"""
from .base import Backend
from .registry import get_backend, register_backend

# Register built-in backends (postgresql; others are stubs until implemented)
from . import postgresql  # noqa: F401

__all__ = ["Backend", "get_backend", "register_backend"]
