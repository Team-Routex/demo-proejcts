"""
raft.serialization.base
~~~~~~~~~~~~~~~~~~~~~~~

Request/response serializers implemented with **Pydantic v2**.

- **Field helpers:** :mod:`raft.serialization.fields` (``IntegerField``, ``CharField``,
  ``EmailField``) with ``read_only`` / ``write_only`` for input stripping and OpenAPI
  ``readOnly`` / ``writeOnly``.
- **Field-level validation:** define ``validate_<fieldname>(self, value)`` (no decorator).
  You may still use Pydantic ``field_validator`` / ``Field(...)`` if you prefer.
- **Object-level validation:** ``validate(self, attrs)`` where ``attrs`` includes
  write-only values; optional return dict is merged into the model. Raise
  :func:`validation_error` or ``ValueError`` on failure.
- **Inbound:** ``Serializer(data=request_dict)``, ``Serializer.from_payload(data)``, or
  ``await validate_body(request, MySerializer)``.
- **Outbound:** ``Serializer(instance=obj).data``, ``serializer.data`` after validation,
  or class helper ``Serializer.serialize(instance)``.

OpenAPI / Swagger: serializer classes are Pydantic models; :func:`raft.openapi.schema.build_openapi_schema`
uses ``model_json_schema()`` and strips internal ``raft_*`` keys from published JSON Schemas.
"""

from __future__ import annotations

import inspect
from typing import Any, Self, TypeVar

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic_core import ValidationError as CoreValidationError

T = TypeVar("T", bound="Serializer")


def validation_error(errors: dict[str, str], *, title: str = "ValidationError") -> None:
    """Raise a structured validation error (field → message mapping)."""
    line_errors = [
        {
            "type": "value_error",
            "loc": (field,),
            "input": None,
            "ctx": {"error": message},
        }
        for field, message in errors.items()
    ]
    raise CoreValidationError.from_exception_data(title, line_errors)


def _unwrap_classmethod(val: Any) -> Any:
    return val.__func__ if isinstance(val, classmethod) else val


def _attrs_for_object_validate(model: Serializer) -> dict[str, Any]:
    """Like ``model_dump()`` but includes write-only fields (for ``validate(self, attrs)``)."""
    return {name: getattr(model, name) for name in type(model).model_fields}


def _field_validator_callable(cls: type, fname: str) -> Any:
    """Return ``validate_<fname>`` defined on *cls* or its subclasses (most derived wins)."""
    for c in cls.__mro__:
        if c is Serializer or c is BaseModel or c is object:
            continue
        raw = c.__dict__.get(f"validate_{fname}")
        if raw is not None:
            return _unwrap_classmethod(raw)
    return None


def _run_hook_validators(self: Serializer) -> Serializer:
    """Run ``validate_<field>(self, value)`` in field order, then ``validate(self, attrs)``."""
    cls = type(self)
    updates: dict[str, Any] = {}
    for fname in cls.model_fields:
        hook = _field_validator_callable(cls, fname)
        if hook is None:
            continue
        sig = inspect.signature(hook)
        params = list(sig.parameters.keys())
        if not params:
            continue
        first = params[0]
        value = getattr(self, fname)
        try:
            if first == "self" and len(params) >= 2:
                new_val = hook(self, value)
            elif first == "cls" and len(params) >= 2:
                new_val = hook(cls, value)
            elif len(params) == 1:
                new_val = hook(value)
            else:
                new_val = hook(cls, value)
        except ValueError as exc:
            validation_error({fname: str(exc)})
        if new_val is not value:
            updates[fname] = new_val
    if updates:
        self = self.model_copy(update=updates)

    validate_fn = None
    for c in cls.__mro__:
        if c is Serializer or c is BaseModel or c is object:
            continue
        if "validate" in c.__dict__:
            validate_fn = c.__dict__["validate"]
            break
    if validate_fn is not None:
        raw = _unwrap_classmethod(validate_fn)
        sig = inspect.signature(raw)
        attrs = _attrs_for_object_validate(self)
        try:
            if len(sig.parameters) >= 2:
                result = raw(self, attrs)
            else:
                result = raw(self)
        except ValueError as exc:
            validation_error({"non_field_errors": str(exc)})
        if isinstance(result, dict):
            allowed = {k: v for k, v in result.items() if k in cls.model_fields}
            if allowed:
                self = self.model_copy(update=allowed)
    return self


class Serializer(BaseModel):
    """Base class for request/response schemas (validation, read/write flags, OpenAPI).

    **DRF-style usage (no decorators on hooks)::**

        class UserSerializer(Serializer):
            id: int | None = IntegerField(read_only=True, default=None)
            username: str = CharField()
            age: int = IntegerField()

            def validate_age(self, value: int) -> int:
                if value < 18:
                    raise ValueError("Age must be at least 18.")
                return value

            def validate(self, attrs: dict) -> None:
                ...

        s = UserSerializer(data=request_dict)
        if s.is_valid():
            payload = s.data

    **Class helper (same as ``Serializer(instance).data`` for plain dict/ORM)::**

        UserSerializer.serialize({"id": 1, "username": "a", "age": 21})
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _raft_strip_read_only_from_input(cls, data: Any) -> Any:
        if data is None or not isinstance(data, dict):
            return data
        strip: list[str] = []
        for fname, finfo in cls.model_fields.items():
            extra = finfo.json_schema_extra
            if isinstance(extra, dict) and extra.get("raft_read_only"):
                strip.append(fname)
        return {k: v for k, v in data.items() if k not in strip}

    def __init__(
        self,
        /,
        *args: Any,
        data: dict[str, Any] | None = None,
        instance: Any | None = None,
        partial: bool = False,
        **kwargs: Any,
    ) -> None:
        if data is not None and instance is None and not kwargs and not args:
            validated = type(self).model_validate(data)
            super().__init__(**{k: getattr(validated, k) for k in type(self).model_fields})
            return
        if instance is not None and data is None and not kwargs and not args:
            if isinstance(instance, dict):
                validated = type(self).model_validate(instance)
            else:
                validated = type(self).model_validate(instance, from_attributes=True)
            super().__init__(**{k: getattr(validated, k) for k in type(self).model_fields})
            return
        kwargs.pop("partial", None)
        super().__init__(*args, **kwargs)

    def is_valid(self, *, raise_exception: bool = False) -> bool:
        """Always ``True`` if the instance was constructed successfully (validation is eager)."""
        return True

    @property
    def errors(self) -> list[Any]:
        """Reserved for future non-raising validation; currently always empty."""
        return []

    @property
    def validated_data(self) -> dict[str, Any]:
        """Validated input as a dict (omits ``read_only`` fields, like typical input payloads)."""
        out: dict[str, Any] = {}
        for name, finfo in type(self).model_fields.items():
            extra = finfo.json_schema_extra
            if isinstance(extra, dict) and extra.get("raft_read_only"):
                continue
            out[name] = getattr(self, name)
        return out

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Build a JSON-ready dict for *instance* (override like DRF). Default: validate then ``model_dump``."""
        cls = type(self)
        if isinstance(instance, cls):
            return instance.model_dump(mode="json")
        if isinstance(instance, dict):
            return cls.model_validate(instance).model_dump(mode="json")
        if isinstance(instance, BaseModel) and not isinstance(instance, Serializer):
            return cls.model_validate(instance.model_dump()).model_dump(mode="json")
        return cls.model_validate(instance, from_attributes=True).model_dump(mode="json")

    @property
    def data(self) -> dict[str, Any]:
        """Outgoing representation for this serializer (``to_representation(self)``)."""
        return self.to_representation(self)

    @classmethod
    def serialize(cls: type[T], instance: Any) -> dict[str, Any]:
        """Serialize *instance* to JSON-ready dict (class-level convenience)."""
        if isinstance(instance, cls):
            return instance.to_representation(instance)
        if isinstance(instance, dict):
            temp = cls.model_validate(instance)
        else:
            temp = cls.model_validate(instance, from_attributes=True)
        return temp.to_representation(instance)

    @classmethod
    def serialize_many(cls: type[T], instances: list[Any]) -> list[dict[str, Any]]:
        """Serialize a list of objects (list endpoints)."""
        return [cls.serialize(item) for item in instances]

    @classmethod
    def model_validate(cls: type[T], obj: Any, /, **kwargs: Any) -> T:  # type: ignore[override]
        """Validate *obj* then run ``validate_<field>`` / ``validate`` hooks once."""
        inst = super(Serializer, cls).model_validate(obj, **kwargs)
        return _run_hook_validators(inst)

    @classmethod
    def from_payload(cls: type[T], data: dict[str, Any]) -> T:
        """Parse and validate a JSON-like dict (typical request body)."""
        return cls.model_validate(data)
