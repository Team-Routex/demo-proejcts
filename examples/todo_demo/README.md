# Raft todo demo

Small example with:

- **REST** — `routes/` + `Serializer` classes for request/response bodies
- **OpenAPI / Swagger** — `/docs` and `/openapi.json`

**No ORM** (in-memory list) and **no GraphQL**.

## Run

```bash
cd examples/todo_demo
uv sync
uv run uvicorn app:app --reload --host 127.0.0.1 --port 8020
```

## Layout

| Path | Role |
|------|------|
| `app.py` | `Raft()` app, OpenAPI router |
| `serializers/todo.py` | `CreateTodoSerializer`, `TodoPatchSerializer`, `TodoOutSerializer` |
| `routes/todos.py` | CRUD over `_store` |
