# Changelog

All notable changes to Raft Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

> Changes staged for the next release.

---

## [0.1.0] — 2026-03-06

Initial public release of **Raft Framework** — a Django-like, ASGI-native Python web
framework with hybrid routing.

### Added

#### Core

- `Raft` — main ASGI application class; composes routing, middleware, sessions, and
  error handling into a single object.
- `RaftRequest` — async-capable request wrapper exposing `method`, `path`, `headers`,
  `query_params`, `path_params`, `body()`, `json()`, `form()`, and `session`.
- `RaftResponse` — structured JSON envelope (`status / message / data / errors`) with
  class-method shortcuts: `ok()`, `created()`, `bad_request()`, `not_found()`,
  `server_error()`, and more.
- `RawResponse` — low-level byte-level response for HTML, redirects, file downloads,
  and any non-JSON content type.

#### Routing

- `Router` — hybrid routing supporting both **decorator style** and
  **URL-conf style** (Django-like `add_routes()`).
- `Route` — dataclass mapping a URL pattern to a handler, with `methods`, `name`,
  and OpenAPI metadata fields (`tags`, `summary`, `request_body`, `responses`).
- `{param}` path parameter syntax with automatic regex compilation and extraction
  into `request.path_params`.
- `Router.include_router()` — nested router composition with prefix propagation.
- `Raft.include_router()` and `Raft.add_route()` / `Raft.add_routes()` for app-level
  route registration.

#### Views

- `View` — base class for **class-based views** (CBVs); implement `get()`, `post()`,
  `put()`, `patch()`, `delete()` to handle HTTP methods cleanly.
- `View.as_view()` — returns an ASGI-compatible callable for route registration,
  dispatching to the correct method handler or raising `405 Method Not Allowed`.
- **Function-based views** (FBVs) supported natively via `@router.route()` and
  `@app.route()` decorators.

#### Middleware

- `MiddlewarePipeline` — ordered middleware chain; each layer wraps `call_next`.
- Built-in middleware (all opt-in per-app via `Raft(enable_*=True/False)`):
  - **CORS** — configurable `Access-Control-Allow-*` headers.
  - **CSRF** — double-submit cookie protection for mutating requests.
  - **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`,
    `Strict-Transport-Security`, `Referrer-Policy`, `Permissions-Policy`.
  - **XSS filtering** — scans query params and body fields for common script
    injection patterns; returns `400` on detection.
  - **SQLi filtering** — scans query params and body fields for SQL injection
    keywords and returns `400` on detection.
- `app.add_middleware()` for registering custom middleware callables.

#### Validation

- `validate_body(request, Model)` — async helper; parses the JSON request body and
  validates it against a Pydantic v2 `BaseModel`, raising `422 Unprocessable Entity`
  with structured field errors on failure.
- `validate_query(request, Model)` — validates query-string parameters against a
  Pydantic model with the same error contract.

#### Session Management

- `InMemorySessionStore` — thread-safe in-process session store backed by a dict.
- Cookie-based session transport using `itsdangerous` `URLSafeTimedSerializer`
  signed cookies; secret key sourced from `settings.SECRET_KEY`.
- `request.session` — dict-like interface for reading and writing session data
  across requests.

#### Configuration

- `RaftSettings` singleton — reads from environment variables or a `.env` file via
  `python-decouple`.
- Fields: `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ORIGINS`, `SESSION_TTL`,
  `SESSION_COOKIE_NAME`, `LOG_LEVEL`.
- `.env.example` template committed to the repository.

#### Exceptions

- `HTTPException` — base exception class; carries `status_code`, `message`, and
  `errors` list; automatically serialised to the `RaftResponse` envelope.
- Subclasses: `BadRequest (400)`, `Unauthorized (401)`, `Forbidden (403)`,
  `NotFound (404)`, `MethodNotAllowed (405)`, `ValidationError (422)`,
  `InternalServerError (500)`.
- Global exception handler converts unhandled `HTTPException` instances into
  structured JSON responses; unhandled Python exceptions yield `500`.

#### GraphQL

- `GraphQLRouter` — mounts a [Strawberry](https://strawberry.rocks/) `Schema` onto a
  `Router` at a configurable path (default `/graphql`).
- Supports `POST` (query/mutation execution) and `GET` (GraphiQL IDE when
  `DEBUG=True`).

#### OpenAPI / Interactive Docs

- `OpenAPIRouter` — mounts three documentation endpoints onto any `Router`:
  - `GET /openapi.json` — lazily generated OpenAPI 3.0.3 JSON specification;
    schema is built on first request so all registered routes are captured.
  - `GET /docs` — [Swagger UI](https://swagger.io/tools/swagger-ui/) served via
    CDN (`swagger-ui-dist@5.11.0` from unpkg).
  - `GET /redoc` — [ReDoc](https://redocly.com/redoc/) served via CDN
    (`redoc@latest` from jsDelivr).
- `build_openapi_schema()` — introspects `Route` objects and produces a full
  OpenAPI 3.0.3 dict including:
  - Path parameters auto-extracted from `{param}` syntax.
  - Per-operation `tags`, `summary`, and docstring `description`.
  - Request body schema from a Pydantic `BaseModel` (via `model_json_schema()`);
    `$defs` hoisted into `components/schemas`.
  - Response schemas with configurable status codes.
  - Default `400 / 422 / 500` responses on every operation.
- `OpenAPIRouter.invalidate_cache()` — force schema rebuild if routes are added
  dynamically after startup.
- `tags`, `summary`, `request_body`, `responses` fields added to `Route` dataclass
  and forwarded through `Router.route()`, `Raft.route()`, and
  `Router.include_router()`.

#### CLI

- `raft` command-line tool built with [Click](https://click.palletsprojects.com/)
  and [Rich](https://rich.readthedocs.io/).
- `raft init [PROJECT_NAME]` — interactive project scaffolding wizard; prompts for
  OpenAPI, REST vs GraphQL, ORM, Celery, WebSocket, and `.env` preferences; writes
  `app.py`, `pyproject.toml`, and `.env`.
- `raft runserver` — launches the uvicorn development server with hot-reload via
  `watchfiles`.
- `raft check` — validates project configuration and reports issues via Rich output.

#### Development Server

- `uvicorn` integration with `watchfiles`-powered hot-reload.
- Structured access log middleware: `HH:MM:SS  METHOD /path → STATUS  (Xms)  ip=…`.

#### Project Scaffolding

- `pyproject.toml` with `hatchling` build backend and `uv`-compatible
  `[tool.uv.sources]` local-path resolution.
- `.gitignore` pre-configured for Python, uv, and common editors.
- `README.md` with quick-start guide.
- MIT `LICENSE`.

### Demo Application

- `todo_project/` — full **Todo REST API** demonstrating the framework:
  - 9 CRUD endpoints under `/todos` using FBVs on a `Router(prefix="/todos")`.
  - `TodoToggleView` CBV at `/todos/{id}/toggle`.
  - Pydantic schemas (`CreateTodoSchema`, `UpdateTodoSchema`) with body validation.
  - In-memory `TodoStore` with create / read / update / delete / filter operations.
  - Session-scoped ownership (`GET /todos/mine`).
  - Aggregate stats endpoint (`GET /todos/stats`).
  - Custom `request_logger_middleware` and `session_id_middleware`.
  - `OpenAPIRouter` mounted with full per-route OpenAPI metadata.
  - Interactive docs live at `/docs`, `/redoc`, and `/openapi.json`.

### Dependencies

| Package | Version | Purpose |
|---|---|---|
| `uvicorn[standard]` | ≥ 0.30 | ASGI server |
| `pydantic` | ≥ 2.0 | Validation & schema generation |
| `python-decouple` | ≥ 3.8 | `.env` / env-var config |
| `python-multipart` | ≥ 0.0.9 | Form / file upload parsing |
| `itsdangerous` | ≥ 2.1 | Signed session cookies |
| `strawberry-graphql` | ≥ 0.230 | GraphQL integration |
| `click` | ≥ 8.1 | CLI framework |
| `rich` | ≥ 13.0 | Terminal formatting |
| `watchfiles` | ≥ 0.21 | Hot-reload file watching |
| `jinja2` | ≥ 3.1 | Template rendering |

---

[Unreleased]: https://github.com/raft-framework/raft-framework/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/raft-framework/raft-framework/releases/tag/v0.1.0
