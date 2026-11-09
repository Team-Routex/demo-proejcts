"""
raft.core.type_enforcement
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automatic parameter binding and type enforcement for Raft view handlers.

Works like TypeScript vs JavaScript — automatically, based on whether a
function parameter has a Python type annotation:

    # STRICT (annotated) — automatically validates & coerces; 422 on failure
    async def get_user(request, user_id: int, page: int = 1):
        ...

    # LAX (unannotated) — passes raw string/value, no 422 raised
    async def get_user(request, user_id, q=""):
        ...

    # MIXED — each parameter is handled individually
    async def search(request, item_id: int, q, limit: int = 20):
        ...

Sources of parameter values (resolved in this order):
    1. Path parameters  (from URL pattern ``{id}``)
    2. Query parameters (from ``?key=value``)
    3. Request body     (JSON dict key matching parameter name)

The ``request`` parameter (or any parameter typed as ``RaftRequest``) is
always injected directly with no coercion.
"""

from __future__ import annotations

import inspect
import types
import uuid
from datetime import datetime, date, time
from typing import Any, Union, get_args, get_origin, get_type_hints

from pydantic import BaseModel

from raft.core.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def bind_and_call_handler(handler: Any, request: Any, path_params: dict[str, str]) -> Any:
    """Inspect *handler* signature, bind request parameters, and call it.

    - Annotated parameters are strictly coerced; 422 on failure.
    - Unannotated parameters receive raw values without type errors.
    - The ``request`` parameter is always injected as-is.
    """
    sig, hints = _get_signature_and_hints(handler)
    if sig is None:
        return await handler(request)

    params = list(sig.parameters.values())
    if not params:
        return await handler()

    # Detect if this is a classic single-arg view: only `request` parameter.
    non_request_params = [
        p for p in params
        if not _is_request_param(p.name, _get_annotation(p, hints))
    ]
    if not non_request_params:
        # Classic handler(request) — call directly with no binding overhead.
        return await handler(request)

    # Load the body lazily once.
    body_data: dict[str, Any] | None = None
    body_loaded = False

    bound: dict[str, Any] = {}
    errors: list[str] = []

    for param in params:
        name = param.name
        annotation = _get_annotation(param, hints)

        # --- inject the request object automatically ---
        if _is_request_param(name, annotation):
            bound[name] = request
            continue

        has_annotation = annotation is not inspect.Parameter.empty
        has_default = param.default is not inspect.Parameter.empty

        # --- resolve value: path → query → body ---
        raw, source = _resolve_raw(name, request, path_params)

        if source == "missing":
            # Value absent from path and query; try body.
            if not body_loaded:
                body_data = await _load_body(request)
                body_loaded = True

            if body_data is not None and name in body_data:
                raw = body_data[name]
                source = "body"
            elif has_default:
                # Use Python's default by not including in bound dict.
                continue
            elif not has_annotation:
                # Unannotated + no default + no value → pass None silently.
                bound[name] = None
                continue
            else:
                # Annotated + required + absent → 422.
                errors.append(f"'{name}' is required")
                continue

        # --- lax: no annotation → pass through unchanged ---
        if not has_annotation:
            bound[name] = raw
            continue

        # --- strict: annotated → coerce to declared type ---
        coerced, err = _coerce(name, raw, annotation)
        if err:
            errors.append(err)
        else:
            bound[name] = coerced

    if errors:
        raise ValidationError(
            message="Request validation failed",
            errors=errors,
        )

    return await handler(**bound)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _get_signature_and_hints(handler: Any) -> tuple[inspect.Signature | None, dict[str, Any]]:
    """Return (signature, resolved_type_hints) for *handler*."""
    try:
        unwrapped = inspect.unwrap(handler)
    except (TypeError, ValueError):
        unwrapped = handler

    try:
        sig = inspect.signature(unwrapped)
    except (TypeError, ValueError):
        return None, {}

    hints: dict[str, Any] = {}
    try:
        hints = get_type_hints(unwrapped)
    except Exception:
        pass

    return sig, hints


def _get_annotation(param: inspect.Parameter, hints: dict[str, Any]) -> Any:
    """Get resolved type annotation for *param*, respecting PEP 563 string annotations."""
    if param.name in hints:
        return hints[param.name]

    ann = param.annotation
    if ann is inspect.Parameter.empty:
        return inspect.Parameter.empty

    if isinstance(ann, str):
        cleaned = ann.strip()
        if cleaned in _STRING_TYPE_MAP:
            return _STRING_TYPE_MAP[cleaned]

    return ann


_STRING_TYPE_MAP: dict[str, Any] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "bytes": bytes,
    "UUID": uuid.UUID,
    "uuid.UUID": uuid.UUID,
    "datetime": datetime,
    "datetime.datetime": datetime,
    "date": date,
    "datetime.date": date,
    "time": time,
    "datetime.time": time,
    "RaftRequest": "RaftRequest",
    "raft.core.request.RaftRequest": "RaftRequest",
}


def _is_request_param(name: str, annotation: Any) -> bool:
    """True when parameter is the request object slot."""
    if name == "request":
        return True
    if annotation is inspect.Parameter.empty:
        return False
    if annotation == "RaftRequest":
        return True
    try:
        from raft.core.request import RaftRequest
        return annotation is RaftRequest
    except ImportError:
        return False


def _resolve_raw(
    name: str,
    request: Any,
    path_params: dict[str, str],
) -> tuple[Any, str]:
    """Return (value, source) from path → query. Source is 'missing' if absent."""
    # 1. Path params
    if name in path_params:
        return path_params[name], "path"

    # 2. Query params
    qp = getattr(request, "query_params", {})
    values = qp.get(name)
    if values:
        raw = values[0] if isinstance(values, list) else values
        return raw, "query"

    return None, "missing"


async def _load_body(request: Any) -> dict[str, Any] | None:
    """Attempt to read and parse the request body as JSON or form data."""
    try:
        data = await request.json()
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    try:
        form = await request.form()
        if isinstance(form, dict) and form:
            return form
    except Exception:
        pass
    return None


def _coerce(name: str, raw: Any, annotation: Any) -> tuple[Any, str | None]:
    """
    Coerce *raw* to *annotation*.

    Returns (coerced_value, None) on success or (None, error_message) on failure.
    """
    # Handle Optional[X] / Union[X, None] — unwrap to X.
    inner = _unwrap_optional(annotation)
    if inner is not None:
        if raw is None or raw == "":
            return None, None
        annotation = inner

    # Pydantic BaseModel — validate dict.
    if _is_pydantic_model(annotation):
        if not isinstance(raw, dict):
            return None, f"'{name}' must be an object (got {type(raw).__name__})"
        try:
            return annotation.model_validate(raw), None
        except Exception as exc:
            return None, f"'{name}': {exc}"

    # Scalar coercions.
    converter = _SCALAR_CONVERTERS.get(annotation)
    if converter is not None:
        try:
            return converter(raw), None
        except (ValueError, TypeError) as exc:
            expected = getattr(annotation, "__name__", str(annotation))
            return None, f"'{name}' must be {expected} (got {raw!r}): {exc}"

    # Unknown annotation — pass raw through without error.
    return raw, None


def _is_pydantic_model(annotation: Any) -> bool:
    try:
        return isinstance(annotation, type) and issubclass(annotation, BaseModel)
    except TypeError:
        return False


def _unwrap_optional(annotation: Any) -> Any | None:
    """If annotation is Optional[X] (Union[X, None] or X | None), return X. Else None."""
    origin = get_origin(annotation)
    is_union = origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)
    if is_union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in ("true", "1", "yes", "on"):
            return True
        if lower in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"Cannot convert {value!r} to bool")
    return bool(value)


def _to_uuid(value: Any) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _to_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _to_time(value: Any) -> time:
    if isinstance(value, time):
        return value
    return time.fromisoformat(str(value))


# Mapping of annotation type → converter callable.
_SCALAR_CONVERTERS: dict[type, Any] = {
    int: int,
    float: float,
    str: str,
    bool: _to_bool,
    bytes: lambda v: v.encode("utf-8") if isinstance(v, str) else bytes(v),
    uuid.UUID: _to_uuid,
    datetime: _to_datetime,
    date: _to_date,
    time: _to_time,
}


def check_routes_with_mypy(routes: list[Any]) -> tuple[str, str, int]:
    """Run Mypy static type checker on Python source files containing registered routes.

    Returns (stdout, stderr, exit_status).
    """
    try:
        from mypy import api
    except ImportError:
        return ("", "mypy is not installed in environment", 1)

    files: set[str] = set()
    for route in routes:
        handler = getattr(route, "handler", None)
        if handler is None:
            continue
        try:
            unwrapped = inspect.unwrap(handler)
            mod = inspect.getmodule(unwrapped)
            if mod and getattr(mod, "__file__", None):
                filepath = str(mod.__file__)
                if filepath.endswith(".py") and "site-packages" not in filepath:
                    files.add(filepath)
        except Exception:
            pass

    if not files:
        return ("", "No route handler files discovered for Mypy checking", 0)

    args = ["--ignore-missing-imports", "--follow-imports=skip"] + list(files)
    stdout, stderr, status = api.run(args)
    return stdout, stderr, status

