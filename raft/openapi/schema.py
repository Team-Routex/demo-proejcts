"""
raft.openapi.schema
~~~~~~~~~~~~~~~~~~~

Builds an OpenAPI 3.0.3 schema dict by introspecting a Router's routes.

Each registered Route can carry optional metadata (tags, summary,
request_body, responses) that enriches the generated spec.  Without any
metadata the builder still produces a valid spec using path parameters,
HTTP methods, and handler docstrings.

Usage::

    from raft.openapi.schema import build_openapi_schema
    spec = build_openapi_schema(app.router, title="My API", version="1.0.0")
"""

from __future__ import annotations

import inspect
import re
from typing import Any

from pydantic import BaseModel

from raft.core.router import Route, Router

# ---------------------------------------------------------------------------
# JSON Schema → OpenAPI (strip framework-only keys from Pydantic output)
# ---------------------------------------------------------------------------


def _strip_internal_json_schema_keys(obj: Any) -> Any:
    """Drop ``raft_*`` entries so Swagger/OpenAPI only show standard JSON Schema."""
    if isinstance(obj, dict):
        return {
            str(k): _strip_internal_json_schema_keys(v)
            for k, v in obj.items()
            if not (isinstance(k, str) and k.startswith("raft_"))
        }
    if isinstance(obj, list):
        return [_strip_internal_json_schema_keys(x) for x in obj]
    return obj


def _pydantic_model_openapi_schema(
    model: type[BaseModel],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """``model_json_schema()`` root and ``$defs``, with internal ``raft_*`` keys stripped."""
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})
    cleaned_defs = {k: _strip_internal_json_schema_keys(v) for k, v in defs.items()}
    root = _strip_internal_json_schema_keys(raw)
    return root, cleaned_defs


# ---------------------------------------------------------------------------
# Built-in Raft envelope schema component (reused for all default responses)
# ---------------------------------------------------------------------------

_RAFT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Standard Raft Framework response envelope",
    "properties": {
        "status": {
            "type": "boolean",
            "description": "True on success, False on error",
            "example": True,
        },
        "message": {
            "type": "string",
            "description": "Human-readable result description",
            "example": "Success",
        },
        "data": {
            "description": "Response payload (object, array, or null)",
            "nullable": True,
        },
        "errors": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Omitted on success (status true). On failure, omitted unless there "
                "is at least one non-empty error string."
            ),
            "example": ["field: invalid value"],
        },
    },
    "required": ["status", "message"],
}


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

def build_openapi_schema(
    router: Router,
    *,
    title: str = "Raft API",
    version: str = "0.1.0",
    description: str = "",
    servers: list[dict[str, str]] | None = None,
    exclude_paths: set[str] | None = None,
) -> dict[str, Any]:
    """Build a full OpenAPI 3.0.3 schema dict from *router*'s routes.

    Parameters:
        router: The ``Router`` (or ``Raft`` app's ``.router``) to introspect.
        title: API title shown in Swagger UI / ReDoc.
        version: API version string.
        description: Optional Markdown description for the API.
        servers: List of server objects, e.g. ``[{"url": "http://localhost:8000"}]``.
        exclude_paths: Set of paths to omit from the schema (e.g. ``/docs``).

    Returns:
        A dict that serializes to a valid OpenAPI 3.0.3 JSON document.
    """
    exclude = exclude_paths or set()
    paths: dict[str, Any] = {}
    components_schemas: dict[str, Any] = {"Response": _RAFT_RESPONSE_SCHEMA}

    for route in router.routes:
        if route.path in exclude:
            continue

        openapi_path = route.path
        methods = route.methods or ["GET"]

        if openapi_path not in paths:
            paths[openapi_path] = {}

        # Extract {param} names from the path
        param_names: list[str] = re.findall(r"\{(\w+)\}", openapi_path)
        path_parameters: list[dict[str, Any]] = [
            {
                "name": p,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
                "description": f"Path parameter: {p}",
            }
            for p in param_names
        ]

        for method in methods:
            operation = _build_operation(
                route=route,
                method=method,
                path_parameters=path_parameters,
                components_schemas=components_schemas,
            )
            paths[openapi_path][method.lower()] = operation

    schema: dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": title,
            "version": version,
        },
        "paths": paths,
        "components": {"schemas": components_schemas},
    }

    if description:
        schema["info"]["description"] = description

    if servers:
        schema["servers"] = servers

    return schema


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_operation(
    route: Route,
    method: str,
    path_parameters: list[dict[str, Any]],
    components_schemas: dict[str, Any],
) -> dict[str, Any]:
    """Build a single OpenAPI operation object for one HTTP method."""
    op: dict[str, Any] = {}

    # Summary — prefer explicit, fall back to auto-generated
    op["summary"] = route.summary or _auto_summary(route.handler, method, route.path)

    # Description — handler docstring
    doc = inspect.getdoc(route.handler)
    if doc:
        op["description"] = doc

    # Tags
    if route.tags:
        op["tags"] = route.tags

    # Stable operation ID
    handler_name = getattr(route.handler, "__name__", "handler")
    op["operationId"] = f"{method.lower()}_{handler_name}"

    # Path parameters
    if path_parameters:
        op["parameters"] = path_parameters

    # Request body (only meaningful for mutating methods)
    body_model = route.request_body
    if body_model and method.upper() in ("POST", "PUT", "PATCH"):
        _add_request_body(op, body_model, components_schemas)

    # Responses
    op["responses"] = _build_responses(route, components_schemas)

    return op


def _add_request_body(
    op: dict[str, Any],
    model: type,
    components_schemas: dict[str, Any],
) -> None:
    """Inject requestBody into *op* and register the model in components."""
    if not isinstance(model, type):
        return

    if issubclass(model, BaseModel):
        schema_name = model.__name__
        model_schema, defs = _pydantic_model_openapi_schema(model)
        for k, v in defs.items():
            components_schemas[k] = v
        components_schemas[schema_name] = model_schema
    else:
        return

    op["requestBody"] = {
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
            }
        },
    }


def _build_responses(
    route: Route,
    components_schemas: dict[str, Any],
) -> dict[str, Any]:
    """Build the ``responses`` object for an operation."""
    result: dict[str, Any] = {}

    if route.responses:
        for status_code, value in route.responses.items():
            code_str = str(status_code)

            if isinstance(value, str):
                # String → description + Response envelope reference
                result[code_str] = {
                    "description": value,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Response"}
                        }
                    },
                }

            elif isinstance(value, type) and (
                issubclass(value, BaseModel) or is_serializer_type(value)
            ):
                schema_name = value.__name__
                if is_serializer_type(value):
                    components_schemas[schema_name] = value.json_schema(write=False)
                else:
                    model_schema, defs = _pydantic_model_openapi_schema(value)
                    for k, v in defs.items():
                        components_schemas[k] = v
                    components_schemas[schema_name] = model_schema

                result[code_str] = {
                    "description": "Success",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                        }
                    },
                }
            else:
                result[code_str] = {"description": str(value)}

    # Ensure at least a default success response is present
    if not any(k.startswith("2") for k in result):
        result["200"] = {
            "description": "Success",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Response"}
                }
            },
        }

    # Standard error responses (only added if not explicitly defined)
    for code, desc in [
        ("400", "Bad Request"),
        ("422", "Validation Error"),
        ("500", "Internal Server Error"),
    ]:
        if code not in result:
            result[code] = {
                "description": desc,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Response"}
                    }
                },
            }

    return result


def _auto_summary(handler: Any, method: str, path: str) -> str:
    """Generate a human-readable summary from the handler name."""
    name = getattr(handler, "__name__", "")
    if name and name not in ("<lambda>", "view_handler"):
        # snake_case → Title Case Words
        return " ".join(w.capitalize() for w in name.split("_"))
    # Fallback: METHOD /last-segment
    segment = path.rstrip("/").rsplit("/", 1)[-1]
    return f"{method.upper()} {segment}"
