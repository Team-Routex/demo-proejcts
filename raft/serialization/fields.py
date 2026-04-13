"""
Field helpers with ``read_only`` / ``write_only`` for :class:`raft.serialization.base.Serializer`.

``read_only=True`` — omitted from inbound validation (clients cannot set it on create/update);
still appears in OpenAPI and in :meth:`~raft.serialization.base.Serializer.serialize` / ``.data``.

``write_only=True`` — accepted on input; excluded from ``model_dump`` / API responses
(``exclude=True`` in Pydantic). OpenAPI gets ``writeOnly: true``.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field
from pydantic.fields import PydanticUndefined


def _merge_json_schema_extra(
    read_only: bool,
    write_only: bool,
    base: dict[str, Any] | None,
) -> dict[str, Any]:
    d: dict[str, Any] = dict(base or {})
    if read_only:
        d["readOnly"] = True
        d["raft_read_only"] = True
    if write_only:
        d["writeOnly"] = True
        d["raft_write_only"] = True
    return d


def IntegerField(
    *,
    read_only: bool = False,
    write_only: bool = False,
    default: Any = PydanticUndefined,
    **kwargs: Any,
) -> Any:
    """Integer field with optional ``read_only`` / ``write_only`` flags."""
    jx = _merge_json_schema_extra(
        read_only, write_only, kwargs.pop("json_schema_extra", None)
    )
    exclude = bool(write_only) or bool(kwargs.pop("exclude", False))
    return Field(
        default=default,
        json_schema_extra=jx,
        exclude=exclude,
        repr=not write_only,
        **kwargs,
    )


def CharField(
    *,
    read_only: bool = False,
    write_only: bool = False,
    default: Any = PydanticUndefined,
    **kwargs: Any,
) -> Any:
    """String field with optional ``read_only`` / ``write_only`` flags."""
    jx = _merge_json_schema_extra(
        read_only, write_only, kwargs.pop("json_schema_extra", None)
    )
    exclude = bool(write_only) or bool(kwargs.pop("exclude", False))
    return Field(
        default=default,
        json_schema_extra=jx,
        exclude=exclude,
        repr=not write_only,
        **kwargs,
    )


def BooleanField(
    *,
    read_only: bool = False,
    write_only: bool = False,
    default: Any = PydanticUndefined,
    **kwargs: Any,
) -> Any:
    """Boolean field with optional ``read_only`` / ``write_only`` flags."""
    jx = _merge_json_schema_extra(
        read_only, write_only, kwargs.pop("json_schema_extra", None)
    )
    exclude = bool(write_only) or bool(kwargs.pop("exclude", False))
    return Field(
        default=default,
        json_schema_extra=jx,
        exclude=exclude,
        repr=not write_only,
        **kwargs,
    )


def EmailField(
    *,
    read_only: bool = False,
    write_only: bool = False,
    default: Any = PydanticUndefined,
    **kwargs: Any,
) -> Any:
    """String field with JSON Schema ``format: email`` (use annotation ``str``)."""
    jx = _merge_json_schema_extra(
        read_only, write_only, kwargs.pop("json_schema_extra", None)
    )
    jx.setdefault("format", "email")
    exclude = bool(write_only) or bool(kwargs.pop("exclude", False))
    return Field(
        default=default,
        json_schema_extra=jx,
        exclude=exclude,
        repr=not write_only,
        **kwargs,
    )
