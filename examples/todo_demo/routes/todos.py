"""REST routes for todos (in-memory store + serializers + OpenAPI)."""

from __future__ import annotations

from raft import RaftResponse, Router
from raft.validation.validator import validate_body
from serializers.todo import CreateTodoSerializer, TodoOutSerializer, TodoPatchSerializer

router = Router(prefix="/api/todos")

_store: list[dict] = []
_next_id: list[int] = [0]


@router.route("/", methods=["GET"])
async def list_todos(request):
    data = [TodoOutSerializer.serialize(row) for row in _store]
    return RaftResponse.ok(message="Todos", data=data)


@router.route(
    "/",
    methods=["POST"],
    request_serializer=CreateTodoSerializer,
    response_serializer=TodoOutSerializer,
)
async def create_todo(request):
    body = await validate_body(request, CreateTodoSerializer)
    _next_id[0] += 1
    row = {"id": _next_id[0], "title": body.title, "done": body.done}
    _store.append(row)
    return RaftResponse.created(
        message="Todo created",
        data=TodoOutSerializer.serialize(row),
    )


@router.route(
    "/{todo_id}",
    methods=["GET"],
    response_serializer=TodoOutSerializer,
)
async def get_todo(request):
    try:
        tid = int(request.path_params["todo_id"])
    except (KeyError, ValueError):
        return RaftResponse.bad_request(message="Invalid todo id")
    for row in _store:
        if row["id"] == tid:
            return RaftResponse.ok(message="Todo", data=TodoOutSerializer.serialize(row))
    return RaftResponse.not_found(message="Todo not found")


@router.route(
    "/{todo_id}",
    methods=["PATCH"],
    request_serializer=TodoPatchSerializer,
    response_serializer=TodoOutSerializer,
)
async def patch_todo(request):
    try:
        tid = int(request.path_params["todo_id"])
    except (KeyError, ValueError):
        return RaftResponse.bad_request(message="Invalid todo id")
    patch = await validate_body(request, TodoPatchSerializer)
    for row in _store:
        if row["id"] == tid:
            if patch.title is not None:
                row["title"] = patch.title
            if patch.done is not None:
                row["done"] = patch.done
            return RaftResponse.ok(message="Todo updated", data=TodoOutSerializer.serialize(row))
    return RaftResponse.not_found(message="Todo not found")


@router.route("/{todo_id}", methods=["DELETE"])
async def delete_todo(request):
    try:
        tid = int(request.path_params["todo_id"])
    except (KeyError, ValueError):
        return RaftResponse.bad_request(message="Invalid todo id")
    for i, row in enumerate(_store):
        if row["id"] == tid:
            _store.pop(i)
            return RaftResponse.ok(message="Todo deleted", data={"id": tid})
    return RaftResponse.not_found(message="Todo not found")
