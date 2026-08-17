# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Framework = `raft/` package, `raft` CLI, and `raft init` scaffold output (not the `examples/` tree).

### Added

- **Redis (built-in):** `redis` is a core dependency. Opt in with `RAFT_REDIS_URL` / `RAFT_REDIS_PREFIX`; helpers `get_redis()`, `redis_configured()`, `redis_key()`. Sessions: `RAFT_SESSION_BACKEND=memory|redis`. No separate package install or extra required.
- **JWT auth (`raft.auth`):** `create_access_token`, `decode_access_token`, `get_bearer_token`, `@require_auth()`, optional `jwt_auth_middleware`. Settings: `RAFT_JWT_SECRET` (falls back to `RAFT_SECRET_KEY`), `RAFT_JWT_ALGORITHM` (HS256), `RAFT_JWT_EXPIRE_MINUTES`. Depends on `PyJWT`.
- **View auth on views:** `authentication_classes` / `permission_classes` on CBVs (`JWTAuthentication`, `IsAuthenticated`, `AllowAny`); on `@app.get` / `@router.post` / table `route(...)` as kwargs; FBV decorators `@authentication_classes` / `@permission_classes`. Sets `request.user` and `request.auth`.
- **CLI redesign:** figlet banner (`pyfiglet`) + Rich panels/tables for `raft`, `init`, `runserver`, `check`, and new `raft version`. Scaffolding moved to `raft.cli.scaffold`; shared UI in `raft.cli.ui`.
- **Project commands (`raft run`):** Django-style management scripts in ``commands/`` via ``@command``; ``raft run seed``, ``raft run --help``. Configurable with ``RAFT_COMMANDS_DIR`` (default ``commands``).
- **Serializers rebuilt (`raft.serialization`):** Django-style ``Serializer``, ``StrField`` / ``IntField`` / ``EmailField``, ``validate_body`` / ``validate_query`` / ``validate_form``, read/write flags, OpenAPI via ``request_serializer`` / ``response_serializer``.
- **Multipart hardened:** ``request.form()`` / ``request.files()`` use ``python-multipart``.
- **Rate limiting:** opt-in middleware ``RAFT_RATE_LIMIT_ENABLED`` with memory or Redis backend; reverse-proxy patterns documented in ``DEPLOYMENT.md``.
- **Deployment guide:** ``DEPLOYMENT.md`` (workers, Redis, secrets, OpenAPI off, HSTS, rate limits).
- **Documentation site:** ``docs/index.html`` — comprehensive HTML/CSS/JS docs (beginner → advanced, searchable).
- **Dual-Runtime Type Enforcement ("Raft TypeShield"):** `raft.core.type_enforcement` provides automatic HTTP parameter validation and type coercion (`int`, `float`, `bool`, `str`, `bytes`, `uuid.UUID`, `datetime`, `date`, `time`, Pydantic `BaseModel`). Annotated parameters are strictly coerced (returning HTTP 422 Unprocessable Entity on validation failure); unannotated parameters are passed raw without errors. Integrates Mypy static code analysis via `mypy.api.run` (`app.typecheck_routes()` and `raft check`).
- **Response API:** ``RaftResponse`` renamed to ``Response`` with primary methods ``Response.success()`` and ``Response.error()``; subclass ``Response`` for custom envelopes. ``RaftResponse`` remains a deprecated alias in ``raft.core.response``.

### Breaking

- **`RaftResponse` → `Response`:** import ``from raft import Response``; use ``Response.success()`` instead of ``.ok()``, ``Response.error()`` for failures. OpenAPI envelope schema component renamed to ``Response``.
- **Sessions (production-oriented):** TTL on memory store, cookie `Secure`/`HttpOnly`/`SameSite`/`Domain` settings, dirty tracking (no empty anonymous cookies), logout clears store + cookie, `session.cycle_key()` for ID rotation after login. Redis backend deletes empty payloads.
- **Circuit breaker (`raft.resilience`):** built-in `CircuitBreaker` / `get_circuit()` for outbound calls (CLOSED → OPEN → HALF_OPEN). `CircuitOpenError` maps to HTTP 503 when raised in a view. Sync `call`, async `acall`, and decorator usage.
- **Route autodiscovery (`raft.core.app.Raft`):** project-wide scan for hybrid route modules exporting `router`, `ROUTERS`, or `routes` (`route` / `include`) — not limited to a `routes/` folder. Skips tests/venvs/framework packages. `RAFT_ROUTES_SCAN=project|dir` (default `project`). No manual `app.add_routes()` required. Opt out with `Raft(auto_discover_routes=False)`.
- **Uniform HTTP routing:** method decorators `@app.get` / `@app.post` / `@app.put` / `@app.patch` / `@app.delete` (and the same on `Router`), plus Django-style `route()` / `include()` / `add_routes()`. `@router.route(methods=[...])` remains for multi-method handlers.

- **`raft check` (CLI):** verifies the default ASGI entry (`app` or `main`) imports and defines an `app` attribute.

### Removed

- **`raft.serialization`:** removed legacy custom `Serializer` module (`Serializer`, `StrField`, `IntField`, `validate_body`, etc.). Standardized 100% on **Pydantic (`pydantic.BaseModel`)** for request validation, output schemas, and OpenAPI docs. Added CLI scaffold prompt for Pydantic.
- **GraphQL:** removed Strawberry GraphQL integration (`raft/graphql`), the `raft init` GraphQL prompt/scaffold, GraphQL `raft check` steps, and the `strawberry-graphql` dependency.
- **Jinja2 / template engine:** unused `jinja2` dependency removed; no template-engine integration is planned as a built-in for now. Docs no longer describe RaftSQL as SQLAlchemy-based.

### Changed

- **Routing module consolidation:** `route()` / `include()`, Django-style tables, and project-wide discovery live in `raft.core.router` (former `urls.py` / `route_discovery.py` removed).
- **`raft.core.response.Response` envelope:** `errors` appears only when `status` is false and at least one non-empty error string exists (after trimming); never on success, including `Response.custom`. OpenAPI built-in `Response` schema marks `errors` optional and `required: ["status", "message"]`.
- **`raft.openapi.schema`:** Pydantic `model_json_schema()` output is sanitized before merge into `components/schemas` so internal `raft_*` keys do not appear in Swagger.
- **`raft.security.headers`:** documented that doc pages may set their own `Content-Security-Policy` first; middleware uses `setdefault` and does not overwrite it.
- **`raft init` / scaffold:** no longer writes `bootstrap.structure.json`; Celery prompt removed and `celery` omitted from generated `pyproject.toml`; generated REST `app.py` relies on route autodiscovery instead of manually `include_router` for `routes/home.py`; generated README adjustments.
- **`raft init` / scaffold:** no longer creates a `schemas/` or `serializers/` package. New projects get `routes/` + `views/` (and optional feature dirs).
- **`raft init` / scaffold:** minimal layout — no sample `routes/home.py`, `routes/users.py`, or `models/user.py`. Generated `app.py` is setup-only (no sample `@app.route`). When ORM is enabled, empty `models/__init__.py` plus `setraft.py`.
- **`raft check`:** implemented in `raft/cli/project_checks.py` (PostgreSQL TCP when `setraft` uses PostgreSQL, raftsql import, WebSocket/scheduler starters, route counts, and `pytest -q` unless `--no-tests`). `raft init` no longer writes `raft_check.py`.

### Fixed

- **`raft.openapi.router.OpenAPIRouter`:** `/docs` and `/redoc` were blank in the browser because `security_headers_middleware`’s `default-src 'self'` CSP blocked CDN and inline Swagger/ReDoc bootstrappers. Doc HTML responses now attach a relaxed CSP for those routes only.
- **`raft.cli` dev server (Windows + reload):** uvicorn workers could fail to import `app`; runners add the project root to `PYTHONPATH` and pass `app_dir` / `reload_dirs` to uvicorn.

### Breaking

- **Serializers / validation helpers removed:** `raft.Serializer`, `raft.serialization.*`, `validate_body` / `validate_query`, and related route kwargs / settings are gone. Use `await request.json()` and OpenAPI `request_body` until the new serializer layer lands.

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
- `Response` structured JSON envelope (`status / message / data / errors`) with shortcuts `ok()`, `created()`, `bad_request()`, `not_found()`, `server_error()`, and more.
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
- `HTTPException` base exception class carrying `status_code`, `message`, and `errors`; automatically serialised to the `Response` envelope.
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
