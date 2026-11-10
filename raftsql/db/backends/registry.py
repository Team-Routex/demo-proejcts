"""Backend registry: get_backend(engine_name)."""
from typing import Dict, Type

from .base import Backend

_registry: Dict[str, Type[Backend]] = {}


def register_backend(backend_class: Type[Backend]) -> None:
    _registry[backend_class.name] = backend_class


def get_backend(engine: str) -> Backend:
    if engine not in _registry:
        raise ValueError(f"Unknown backend: {engine}. Registered: {list(_registry.keys())}")
    return _registry[engine]()
