"""Registry of serializer classes (for autodiscovery and OpenAPI components)."""

from __future__ import annotations

from typing import Any

_REGISTERED: dict[str, type[Any]] = {}


def register_serializer(cls: type[Any]) -> type[Any]:
    """Register *cls* by ``__name__`` for OpenAPI and introspection."""
    _REGISTERED[cls.__name__] = cls
    return cls


def unregister_serializer(name: str) -> None:
    _REGISTERED.pop(name, None)


def clear_serializer_registry() -> None:
    _REGISTERED.clear()


def registered_serializers() -> dict[str, type[Any]]:
    return dict(_REGISTERED)
