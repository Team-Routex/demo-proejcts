"""
raft.validation.validator
~~~~~~~~~~~~~~~~~~~~~~~~~

Pydantic-powered request validation helpers.

Provides ``validate_body`` — a convenience that reads the JSON body,
validates it against a Pydantic model, and returns a validated instance
or raises a structured ``ValidationError``.

Usage in a view::

    from pydantic import BaseModel
    from raft.validation.validator import validate_body

    class CreateUser(BaseModel):
        name: str
        email: str

    @router.route("/users", methods=["POST"])
    async def create_user(request):
        user = await validate_body(request, CreateUser)
        return RaftResponse.created(data=user.model_dump())
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from raft.core.exceptions import ValidationError
from raft.core.request import RaftRequest

T = TypeVar("T", bound=BaseModel)


async def validate_body(request: RaftRequest, model: type[T]) -> T:
    """Validate the JSON body of *request* against a Pydantic *model*.

    Parameters:
        request: The current RaftRequest.
        model: A Pydantic BaseModel subclass to validate against.

    Returns:
        A validated instance of *model*.

    Raises:
        raft.core.exceptions.ValidationError: If validation fails, with
        a structured list of error detail dicts.
    """
    data = await request.json()
    try:
        return model.model_validate(data)
    except PydanticValidationError as exc:
        errors = [
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        ]
        detail = exc.errors()
        raise ValidationError(
            message="Validation Error",
            errors=errors,
            detail=detail,
        ) from exc


async def validate_query(request: RaftRequest, model: type[T]) -> T:
    """Validate query parameters against a Pydantic *model*.

    Single-value lists are unwrapped automatically so the model can
    declare ``field: str`` instead of ``field: list[str]``.
    """
    raw = request.query_params
    flat: dict[str, str | list[str]] = {
        k: v[0] if len(v) == 1 else v for k, v in raw.items()
    }
    try:
        return model.model_validate(flat)
    except PydanticValidationError as exc:
        errors = [
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        ]
        raise ValidationError(
            message="Query Validation Error",
            errors=errors,
            detail=exc.errors(),
        ) from exc
