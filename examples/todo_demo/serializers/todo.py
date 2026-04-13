"""Raft ``Serializer`` classes for todo REST bodies and OpenAPI."""

from __future__ import annotations

from raft import Serializer
from raft.serialization.fields import BooleanField, CharField


class CreateTodoSerializer(Serializer):
    """Inbound body for POST /api/todos/ (no ``id`` — server assigns it)."""

    title: str = CharField(min_length=1, max_length=255)
    done: bool = BooleanField(default=False)

    def validate_title(self, value: str) -> str:
        """Optional extra rule; ``min_length=1`` already rejects empty strings."""
        return value.strip()


class TodoPatchSerializer(Serializer):
    title: str | None = None
    done: bool | None = None


class TodoOutSerializer(Serializer):
    id: int
    title: str
    done: bool

    def to_representation(self, instance: object) -> dict[str, object]:
        """Custom JSON shape for list/detail responses (handles dict or serializer instance)."""
        rep = super().to_representation(instance)
        rep["title"] = str(rep["title"]).strip()
        return rep
