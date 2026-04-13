# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Framework = `raft/` package, `raft` CLI, and `raft init` scaffold output (not the `examples/` tree).

### Added

- **Route autodiscovery (`raft.core.app.Raft`):** loads routers from `routes/*.py` under the project root (skips `__init__.py` and `_*.py`). Each module may export `router` or `ROUTERS`. Settings: `RAFT_AUTO_DISCOVER_ROUTES`, `RAFT_ROUTES_DIR`. Opt out with `Raft(auto_discover_routes=False)`.
- **`raft check` (CLI):** verifies the default ASGI entry (`app` or `main`) imports and defines an `app` attribute.
- **`raft.serialization`:** `Serializer` subclass of Pydantic `BaseModel` for shared request/response validation and OpenAPI: `from_payload` / overridden `model_validate` (runs `validate_<field>(self, value)` then `validate(self, attrs)`; optional `validation_error({field: message})`); inbound strip of `read_only` fields; `Serializer(data=…)` / `Serializer(instance=…)`; `.data`, `.validated_data`, `.is_valid()`; instance `to_representation(self, instance)`; class helpers `serialize` / `serialize_many`. Pydantic `field_validator` / `model_validator` remain supported. `validation_error` is exported from `raft` and `raft.serialization`.
- **Field helpers (`raft.serialization.fields`):** `IntegerField`, `CharField`, `EmailField`, `BooleanField` with optional `read_only` / `write_only` (JSON Schema `readOnly` / `writeOnly`, internal `raft_*` markers stripped in published OpenAPI).
- **Serializer autodiscovery:** `Raft()` registers `Serializer` subclasses from `serializers/*.py` (`RAFT_AUTO_DISCOVER_SERIALIZERS`, `RAFT_SERIALIZERS_DIR`); `register_serializer` / `registered_serializers` merge into OpenAPI components via `raft.openapi.schema`.
- **Router OpenAPI kwargs (`raft.core.router`):** `request_serializer` / `response_serializer` aliases for `request_body` / `responses` when declaring routes.

### Changed

- **`raft.core.response.RaftResponse` envelope:** `errors` appears only when `status` is false and at least one non-empty error string exists (after trimming); never on success, including `RaftResponse.custom`. OpenAPI built-in `RaftResponse` schema marks `errors` optional and `required: ["status", "message"]`.
- **`raft.openapi.schema`:** Pydantic `model_json_schema()` output is sanitized before merge into `components/schemas` so internal `raft_*` keys do not appear in Swagger.
- **`raft.security.headers`:** documented that doc pages may set their own `Content-Security-Policy` first; middleware uses `setdefault` and does not overwrite it.
- **`raft init` / scaffold:** no longer writes `bootstrap.structure.json`; Celery prompt removed and `celery` omitted from generated `pyproject.toml`; generated REST `app.py` relies on route autodiscovery instead of manually `include_router` for `routes/home.py`; generated README adjustments.
- **`raft init` / scaffold:** no longer creates a `schemas/` package or `schemas/user.py`. New projects get `serializers/user.py` with `CreateUserSerializer` and `UpdateUserSerializer` (Raft `Serializer` + field helpers) and a `serializers/__init__.py` that re-exports them.

### Fixed

- **`raft.openapi.router.OpenAPIRouter`:** `/docs` and `/redoc` were blank in the browser because `security_headers_middleware`’s `default-src 'self'` CSP blocked CDN and inline Swagger/ReDoc bootstrappers. Doc HTML responses now attach a relaxed CSP for those routes only.
- **`raft.cli` dev server (Windows + reload):** uvicorn workers could fail to import `app`; runners add the project root to `PYTHONPATH` and pass `app_dir` / `reload_dirs` to uvicorn.

### Breaking

- **Serialization class API:** class-level `Serializer.to_representation` / `to_representation_many` were replaced by `Serializer.serialize` / `serialize_many` (Python cannot expose both a classmethod and instance method under the same name as before). Update call sites accordingly.

## [0.0.1-alpha.2] - 2026-03-09

### Added

- Class-based view routes can now be registered without explicit `.as_view()` when using `Route(...)`; `Route` auto-detects `View` subclasses and wraps them.
- OpenAPI docs access control with public/private mode:
	- `RAFT_OPENAPI_DOCS_VISIBILITY=public|private`
	- `RAFT_OPENAPI_DOCS_PASSWORD=...`
	- HTTP Basic auth challenge for `/openapi.json`, `/docs`, and `/redoc` in private mode.
- In-process periodic task scheduler improvements:
	- `repeat=True|False` support on `app.task(...)` and `app.add_task(...)`
	- one-shot task execution via `repeat=False`
	- startup/shutdown lifecycle integration for automatic scheduler start/stop.
- Task autodiscovery system:
	- scans project `tasks/` folder (configurable) and auto-registers periodic jobs
	- new `@periodic_task(...)` decorator for discovery metadata
	- startup logs: `New task detected: ...`
	- settings: `RAFT_AUTO_DISCOVER_TASKS`, `RAFT_TASKS_DIR`.
- WebSocket subsystem:
	- `@app.websocket("/path")` route registration
	- path params for websocket routes
	- `WebSocketManager` room helpers (`join_room`, `leave_room`, room send, broadcast)
	- ASGI websocket dispatch in `Raft` with graceful close for not found (`4404`) and handler errors.
- Custom middleware autodiscovery system:
	- scans project `middleware/` folder and auto-registers `*_middleware` async callables
	- optional explicit `MIDDLEWARE = [...]` support
	- startup logs: `New middleware detected: ...`
	- settings: `RAFT_AUTO_DISCOVER_MIDDLEWARE`, `RAFT_MIDDLEWARE_DIR`.
- CLI scaffolding enhancements (`raft init`):
	- GraphQL is now explicitly optional via `Use GraphQL? [y/N]`; REST-only scaffold is generated when disabled.
	- optional scheduler scaffolding with autodiscovery-ready `tasks/periodic.py`
	- optional websocket scaffolding with `ws/chat.py`
	- optional custom middleware starter file generation (`middleware/request_id.py`)
	- generated project `README.md` now lists enabled/disabled module selections.
	- generated `bootstrap.structure.json` manifest describing selected features and scaffolded directories.

### Changed

- Hardened security middleware behavior:
	- XSS middleware now normalizes encoded payloads and scans query/path/header + JSON/form inputs.
	- SQLi middleware now normalizes payloads (decode/comment/whitespace handling) and scans query/path/header + JSON/form inputs.
	- CSRF middleware now validates same-origin (`Origin`/`Referer` vs `Host`) for mutating methods, supports multiple token sources (`X-CSRF-Token`, `X-XSRF-Token`, cookie/form), and exposes CSRF token in response header/cookie.
- `raft init` file generation now writes with explicit UTF-8 encoding to avoid Windows encoding failures.
- `raft init` prompt flow now avoids redundant options:
	- skips `Use task queue (Celery)?` when built-in scheduler is selected
	- standardized yes/no prompt defaults for a more consistent interactive experience.

### Documentation

- Updated README project structure diagram to include current modules (`openapi`, `tasks`, `websocket`, tests).
- Added task-folder autodiscovery and custom middleware-folder autodiscovery guidance.
- Added easy websocket usage examples and updated CLI prompt examples.

### Testing

- Added/expanded tests for:
	- OpenAPI schema coverage (path params, request body schema, response envelope)
	- Scheduler repeat semantics and lifecycle integration
	- Task autodiscovery from `tasks/`
	- CLI bootstrap structure manifest generation and option-based directory creation
	- CLI prompt flow behavior (Celery prompt skip when scheduler is enabled)
	- WebSocket runtime and scaffold behavior
	- Middleware autodiscovery and detection logging
	- Security middleware hardening (XSS/SQLi/CSRF)
	- CLI scaffold toggles for scheduler/websocket/custom middleware starter.

## [0.0.1-alpha.1] - 2026-03-06

### Added

- `Raft` ASGI application class that composes routing, middleware, sessions, and error handling.
- `RaftRequest` wrapper exposing `method`, `path`, `headers`, `query_params`, `path_params`, `body()`, `json()`, `form()`, and `session`.
- `RaftResponse` structured JSON envelope (`status / message / data / errors`) with shortcuts `ok()`, `created()`, `bad_request()`, `not_found()`, `server_error()`, and more.
- `RawResponse` for non-JSON responses such as HTML, redirects, and file downloads.
- `Router` supporting both decorator-style (`@router.route()`) and URL-conf-style (`add_routes()`) route registration.
- `Route` dataclass with `path`, `handler`, `methods`, `name`, `tags`, `summary`, `request_body`, and `responses` fields.
- `{param}` path parameter syntax with automatic regex compilation and extraction into `request.path_params`.
- `Router.include_router()` for nested router composition with prefix propagation.
- `Raft.include_router()`, `Raft.add_route()`, and `Raft.add_routes()` for app-level route registration.
- `View` base class for class-based views; implement `get()`, `post()`, `put()`, `patch()`, or `delete()` to handle HTTP methods.
- `View.as_view()` returning an ASGI-compatible callable that dispatches to the correct method handler or raises `405 Method Not Allowed`.
- Function-based view (FBV) support via `@router.route()` and `@app.route()` decorators.
- `MiddlewarePipeline` ordered middleware chain where each layer receives `call_next`.
- `app.add_middleware()` for registering custom middleware callables.
- Built-in CORS middleware with configurable `Access-Control-Allow-*` headers.
- Built-in CSRF middleware using double-submit cookie protection for mutating requests.
- Built-in security-headers middleware setting `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy`, and `Permissions-Policy`.
- Built-in XSS-filtering middleware that rejects requests containing common script-injection patterns with `400`.
- Built-in SQL-injection-filtering middleware that rejects requests containing SQL keywords with `400`.
- All built-in middleware layers are individually opt-in via `Raft(enable_cors=…, enable_csrf=…, enable_security_headers=…, enable_xss=…, enable_sqli=…)`.
- `validate_body(request, Model)` async helper for parsing and validating a JSON request body against a Pydantic v2 `BaseModel`; raises `422 Unprocessable Entity` with structured field errors on failure.
- `validate_query(request, Model)` async helper for validating query-string parameters against a Pydantic model with the same error contract.
- `InMemorySessionStore` thread-safe in-process session store.
- Cookie-based session transport using `itsdangerous` `URLSafeTimedSerializer` signed cookies; secret sourced from `settings.SECRET_KEY`.
- `request.session` dict-like interface for reading and writing session data across requests.
- `RaftSettings` singleton that reads `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ORIGINS`, `SESSION_TTL`, `SESSION_COOKIE_NAME`, and `LOG_LEVEL` from environment variables or a `.env` file via `python-decouple`.
- `HTTPException` base exception class carrying `status_code`, `message`, and `errors`; automatically serialised to the `RaftResponse` envelope.
- `BadRequest (400)`, `Unauthorized (401)`, `Forbidden (403)`, `NotFound (404)`, `MethodNotAllowed (405)`, `ValidationError (422)`, and `InternalServerError (500)` exception subclasses.
- Global exception handler converting unhandled `HTTPException` instances to structured JSON; uncaught Python exceptions yield `500`.
- `GraphQLRouter` that mounts a [Strawberry](https://strawberry.rocks/) `Schema` onto a `Router` at a configurable path (default `/graphql`); supports `POST` execution and `GET` GraphiQL IDE when `DEBUG=True`.
- `OpenAPIRouter` that mounts `GET /openapi.json`, `GET /docs` (Swagger UI), and `GET /redoc` (ReDoc) onto any `Router`.
- Lazily generated OpenAPI 3.0.3 JSON specification; schema is built on the first request to `/openapi.json` so all application routes are captured, and cached thereafter.
- `OpenAPIRouter.invalidate_cache()` to force a schema rebuild when routes are added dynamically after startup.
- `build_openapi_schema()` that introspects `Route` objects to produce path parameters, per-operation `tags`, `summary`, docstring descriptions, Pydantic request-body schemas (with `$defs` hoisted into `components/schemas`), configurable response schemas, and default `400 / 422 / 500` responses on every operation.
- Swagger UI served via CDN (`swagger-ui-dist@5.11.0` from unpkg); no extra runtime dependency required.
- ReDoc served via CDN (`redoc@latest` from jsDelivr); no extra runtime dependency required.
- `raft` CLI built with [Click](https://click.palletsprojects.com/) and [Rich](https://rich.readthedocs.io/).
- `raft init [PROJECT_NAME]` interactive scaffolding wizard generating `app.py`, `pyproject.toml`, and `.env`.
- `raft runserver` command that starts uvicorn with `watchfiles`-powered hot-reload.
- `raft check` command that validates project configuration and reports issues.
- Structured access-log middleware emitting `HH:MM:SS  METHOD /path → STATUS  (Xms)  ip=…` on every request.
- `pyproject.toml` using `hatchling` build backend with `uv`-compatible `[tool.uv.sources]` local-path resolution.
- `.env.example` configuration template.
- `.gitignore` pre-configured for Python, uv, and common editors.
- `README.md` quick-start guide and `LICENSE` (MIT).

[Unreleased]: https://github.com/raft-framework/raft-framework/compare/v0.0.1-alpha.2...HEAD
[0.0.1-alpha.2]: https://github.com/raft-framework/raft-framework/compare/v0.0.1-alpha.1...v0.0.1-alpha.2
[0.0.1-alpha.1]: https://github.com/raft-framework/raft-framework/releases/tag/v0.0.1-alpha.1
