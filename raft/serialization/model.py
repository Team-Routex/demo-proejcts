"""
DRF-style ModelSerializer for Raft.

This serializer works with plain Python model-like classes (including dataclasses,
ORM entities, or any object exposing attributes / __dict__). It provides:

- Meta.model / Meta.fields / Meta.exclude
- read_only_fields / write_only_fields
- field-level validation hooks: validate_<field>(value)
- object-level validation hook: validate(attrs)
- create/update/save flow with partial updates
- many=True support
"""

from __future__ import annotations

import inspect
from datetime import date, datetime, time
from typing import Any


class ModelSerializer:
    """DRF-like model serializer with validation + create/update helpers."""

    class Meta:
        model: type[Any] | None = None
        fields: str | list[str] | tuple[str, ...] = "__all__"
        exclude: list[str] | tuple[str, ...] = ()
        read_only_fields: list[str] | tuple[str, ...] = ()
        write_only_fields: list[str] | tuple[str, ...] = ()

    def __init__(
        self,
        instance: Any | list[Any] | None = None,
        data: dict[str, Any] | list[dict[str, Any]] | None = None,
        *,
        many: bool = False,
        partial: bool = False,
    ) -> None:
        self.instance = instance
        self.initial_data = data
        self.many = many
        self.partial = partial
        self._errors: dict[str, Any] = {}
        self._validated_data: dict[str, Any] | list[dict[str, Any]] = {} if not many else []
        self._is_validated = False

        meta_model = getattr(self.Meta, "model", None)
        if meta_model is None:
            raise ValueError(f"{type(self).__name__} must define Meta.model")

        self.model = meta_model
        self._all_fields = self._resolve_fields()
        self._read_only = set(getattr(self.Meta, "read_only_fields", ()) or ())
        self._write_only = set(getattr(self.Meta, "write_only_fields", ()) or ())
        self._writable_fields = [f for f in self._all_fields if f not in self._read_only]
        self._readable_fields = [f for f in self._all_fields if f not in self._write_only]
        self._required_fields = self._resolve_required_fields()

    def _resolve_fields(self) -> list[str]:
        fields = getattr(self.Meta, "fields", "__all__")
        exclude = set(getattr(self.Meta, "exclude", ()) or ())
        if fields == "__all__":
            resolved = self._discover_model_fields()
        else:
            resolved = list(fields)
        return [f for f in resolved if f not in exclude]

    def _discover_model_fields(self) -> list[str]:
        out: list[str] = []
        annotations = getattr(self.model, "__annotations__", {}) or {}
        if annotations:
            out.extend(annotations.keys())
        else:
            sig = inspect.signature(self.model.__init__)
            for name, param in sig.parameters.items():
                if name == "self":
                    continue
                if param.kind in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                ):
                    out.append(name)
        return [name for name in out if not name.startswith("_")]

    def _resolve_required_fields(self) -> set[str]:
        """Fields without constructor defaults are required on create."""
        required: set[str] = set()
        sig = inspect.signature(self.model.__init__)
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            if name not in self._writable_fields:
                continue
            if param.kind not in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                continue
            if param.default is inspect._empty:
                required.add(name)
        return required

    def is_valid(self, *, raise_exception: bool = False) -> bool:
        self._errors = {}
        if self.initial_data is None:
            self._errors = {"non_field_errors": "No input data provided."}
            if raise_exception:
                raise ValueError(self._errors["non_field_errors"])
            return False

        try:
            if self.many:
                if not isinstance(self.initial_data, list):
                    raise ValueError("Expected a list of objects when many=True.")
                validated_list = []
                batch_errors: dict[str, Any] = {}
                for idx, item in enumerate(self.initial_data):
                    cleaned, errors = self._validate_one(item)
                    if errors:
                        batch_errors[str(idx)] = errors
                    else:
                        validated_list.append(cleaned)
                if batch_errors:
                    self._errors = batch_errors
                    if raise_exception:
                        raise ValueError(batch_errors)
                    return False
                self._validated_data = validated_list
            else:
                if not isinstance(self.initial_data, dict):
                    raise ValueError("Expected an object input.")
                cleaned, errors = self._validate_one(self.initial_data)
                if errors:
                    self._errors = errors
                    if raise_exception:
                        raise ValueError(errors)
                    return False
                self._validated_data = cleaned
        finally:
            self._is_validated = True

        return True

    def _validate_one(self, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        errors: dict[str, Any] = {}
        attrs: dict[str, Any] = {}
        unknown = [k for k in payload if k not in self._all_fields]
        if unknown:
            for name in unknown:
                errors[name] = "Unknown field."

        if not self.partial:
            for field in self._required_fields:
                if field not in payload:
                    errors[field] = "This field is required."

        for field in self._writable_fields:
            if field not in payload:
                continue
            value = payload[field]
            hook = getattr(self, f"validate_{field}", None)
            if callable(hook):
                try:
                    value = hook(value)
                except Exception as exc:
                    errors[field] = str(exc)
                    continue
            attrs[field] = value

        validate_obj = getattr(self, "validate", None)
        if callable(validate_obj):
            try:
                maybe = validate_obj(attrs)
                if isinstance(maybe, dict):
                    attrs = maybe
            except Exception as exc:
                errors["non_field_errors"] = str(exc)

        return attrs, errors

    @property
    def errors(self) -> dict[str, Any]:
        return self._errors

    @property
    def validated_data(self) -> dict[str, Any] | list[dict[str, Any]]:
        return self._validated_data

    @property
    def data(self) -> dict[str, Any] | list[dict[str, Any]]:
        if self.many:
            if self.instance is not None:
                return [self.to_representation(obj) for obj in self.instance]  # type: ignore[arg-type]
            if isinstance(self._validated_data, list):
                return [self._as_output_dict(v) for v in self._validated_data]
            return []

        if self.instance is not None:
            return self.to_representation(self.instance)
        if isinstance(self._validated_data, dict):
            return self._as_output_dict(self._validated_data)
        return {}

    def _as_output_dict(self, attrs: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for field in self._readable_fields:
            if field in attrs:
                out[field] = self._normalize_output(attrs[field])
        return out

    def _normalize_output(self, value: Any) -> Any:
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        return value

    def to_representation(self, instance: Any) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for field in self._readable_fields:
            if isinstance(instance, dict):
                value = instance.get(field)
            else:
                value = getattr(instance, field, None)
            out[field] = self._normalize_output(value)
        return out

    def save(self, **kwargs: Any) -> Any:
        if not self._is_validated:
            raise ValueError("Call is_valid() before save().")
        if self._errors:
            raise ValueError("Cannot save invalid serializer data.")

        if self.many:
            validated = self._validated_data if isinstance(self._validated_data, list) else []
            if self.instance is not None:
                updated = []
                for obj, attrs in zip(self.instance, validated):  # type: ignore[arg-type]
                    updated.append(self.update(obj, {**attrs, **kwargs}))
                self.instance = updated
                return updated
            created = [self.create({**attrs, **kwargs}) for attrs in validated]
            self.instance = created
            return created

        validated_one = self._validated_data if isinstance(self._validated_data, dict) else {}
        payload = {**validated_one, **kwargs}
        if self.instance is not None:
            self.instance = self.update(self.instance, payload)
            return self.instance
        self.instance = self.create(payload)
        return self.instance

    def create(self, validated_data: dict[str, Any]) -> Any:
        obj = self.model(**validated_data)
        save_method = getattr(obj, "save", None)
        if callable(save_method):
            save_method()
        return obj

    def update(self, instance: Any, validated_data: dict[str, Any]) -> Any:
        for key, value in validated_data.items():
            setattr(instance, key, value)
        save_method = getattr(instance, "save", None)
        if callable(save_method):
            save_method()
        return instance
