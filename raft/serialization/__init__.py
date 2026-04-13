"""Serializers — validation and JSON representation on top of Pydantic."""

from raft.serialization.base import Serializer, validation_error
from raft.serialization.fields import BooleanField, CharField, EmailField, IntegerField
from raft.serialization.registry import (
    clear_serializer_registry,
    register_serializer,
    registered_serializers,
    unregister_serializer,
)

__all__ = [
    "Serializer",
    "validation_error",
    "IntegerField",
    "CharField",
    "BooleanField",
    "EmailField",
    "register_serializer",
    "registered_serializers",
    "unregister_serializer",
    "clear_serializer_registry",
]
