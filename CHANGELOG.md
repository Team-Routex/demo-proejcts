# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-03-06

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

[Unreleased]: https://github.com/raft-framework/raft-framework/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/raft-framework/raft-framework/releases/tag/v0.1.0
