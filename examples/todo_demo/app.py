"""
Todo demo — REST + Raft serializers + OpenAPI (Swagger)
=======================================================

In-memory todos (no database, no GraphQL).

Run from this directory::

    cd examples/todo_demo
    uv sync
    uv run uvicorn app:app --reload --host 127.0.0.1 --port 8020

- ``GET|POST /api/todos`` — list / create
- ``GET|PATCH|DELETE /api/todos/{id}`` — read / update / delete
- ``GET /docs`` — Swagger UI
- ``GET /openapi.json`` — OpenAPI spec
"""

from __future__ import annotations

from raft import Raft, RaftResponse
from raft.openapi.router import OpenAPIRouter

from routes.todos import router as todos_router

app = Raft()

app.include_router(todos_router)

openapi = OpenAPIRouter(
    app,
    title="Todo demo API",
    version="1.0.0",
    description="In-memory todos with REST serializers and OpenAPI.",
)
app.include_router(openapi.router)


@app.route("/", methods=["GET"])
async def index(request):
    return RaftResponse.ok(
        message="Raft todo demo",
        data={
            "rest": {"list_create": "GET|POST /api/todos", "detail": "/api/todos/{id}"},
            "docs": "/docs",
            "openapi": "/openapi.json",
            "note": "Data is stored in memory only; restarting the server clears todos.",
        },
    )
