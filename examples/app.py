"""
Example Raft Application
========================

Demonstrates all major features of the Raft Framework:
- Function-based views (FBV)
- Class-based views (CBV)
- REST routes
- GraphQL integration
- Request utilities (params, cookies, headers, files)
- Session read/write
- Pydantic validation
- Structured responses
- Custom middleware
"""

import strawberry

from raft import Raft, RaftResponse, RaftRequest, Router, Route
from raft.core.views import View
from raft.core.response import RawResponse
from raft.core.exceptions import HTTPException, NotFound
from raft.graphql.integration import GraphQLRouter
from raft.openapi.router import OpenAPIRouter
from raft.validation.validator import validate_body
from raft.middleware.base import CallNext
from pydantic import BaseModel


# =========================================================================
# 1. Pydantic schemas for validation
# =========================================================================

class CreateItemSchema(BaseModel):
    """Schema for creating an item."""
    name: str
    price: float
    in_stock: bool = True


class UpdateItemSchema(BaseModel):
    """Schema for partial item update."""
    name: str | None = None
    price: float | None = None
    in_stock: bool | None = None


# =========================================================================
# 2. Create the Raft app
# =========================================================================

app = Raft(
    debug=True,
    enable_sessions=True,
    enable_cors=True,
    enable_csrf=False,      # Disabled for REST-API-only usage
    enable_security_headers=True,
    enable_xss=True,
    enable_sqli=True,
)


# =========================================================================
# 3. Custom middleware example
# =========================================================================

async def request_id_middleware(request: RaftRequest, call_next: CallNext) -> RawResponse:
    """Example custom middleware that adds a request ID header."""
    import secrets
    request_id = secrets.token_hex(8)
    request.state["request_id"] = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

app.add_middleware(request_id_middleware)


# =========================================================================
# 4. Simple REST route (FBV — function-based view)
# =========================================================================

@app.route("/", methods=["GET"])
async def index(request: RaftRequest) -> RawResponse:
    """Root endpoint."""
    return RaftResponse.ok(
        message="Welcome to the Raft Example App!",
        data={"version": "0.1.0"},
    )


@app.route("/hello/{name}", methods=["GET"])
async def hello(request: RaftRequest) -> RawResponse:
    """Greet someone by name (path parameter)."""
    name = request.path_params.get("name", "world")
    return RaftResponse.ok(message=f"Hello, {name}!")


# =========================================================================
# 5. Reading query params, headers, cookies
# =========================================================================

@app.route("/info", methods=["GET"])
async def info(request: RaftRequest) -> RawResponse:
    """Demonstrate reading request metadata."""
    return RaftResponse.ok(
        message="Request info",
        data={
            "client_ip": request.client_ip,
            "user_agent": request.user_agent,
            "query_params": request.query_params,
            "example_query": request.get_query_param("q", "not provided"),
            "cookies": request.cookies,
            "accept_header": request.get_header("accept", "not set"),
        },
    )


# =========================================================================
# 6. File upload handling
# =========================================================================

@app.route("/upload", methods=["POST"])
async def upload(request: RaftRequest) -> RawResponse:
    """Handle file uploads."""
    files = await request.files()
    if not files:
        return RaftResponse.bad_request(
            message="No files uploaded",
            errors=["Expected a multipart form with at least one file"],
        )

    file_info = []
    for field_name, uploaded in files.items():
        file_info.append({
            "field": field_name,
            "filename": uploaded.filename,
            "content_type": uploaded.content_type,
            "size_bytes": uploaded.size,
        })

    return RaftResponse.ok(
        message=f"{len(files)} file(s) received",
        data={"files": file_info},
    )


# =========================================================================
# 7. Session read/write
# =========================================================================

@app.route("/session/set", methods=["POST"])
async def session_set(request: RaftRequest) -> RawResponse:
    """Write data to the session."""
    body = await request.json()
    key = body.get("key", "default_key")
    value = body.get("value", "default_value")
    request.session[key] = value
    return RaftResponse.ok(
        message="Session updated",
        data={"key": key, "value": value},
    )


@app.route("/session/get/{key}", methods=["GET"])
async def session_get(request: RaftRequest) -> RawResponse:
    """Read data from the session."""
    key = request.path_params["key"]
    value = request.session.get(key)
    if value is None:
        return RaftResponse.not_found(message=f"No session data for key '{key}'")
    return RaftResponse.ok(
        message="Session data retrieved",
        data={"key": key, "value": value},
    )


# =========================================================================
# 8. Pydantic validation
# =========================================================================

@app.route("/items", methods=["POST"])
async def create_item(request: RaftRequest) -> RawResponse:
    """Create an item with validated input."""
    item = await validate_body(request, CreateItemSchema)
    return RaftResponse.created(
        message="Item created",
        data=item.model_dump(),
    )


# =========================================================================
# 9. Class-based view (CBV)
# =========================================================================

class ItemView(View):
    """CBV that handles GET and PUT for a single item."""

    async def get(self, request: RaftRequest) -> RawResponse:
        item_id = request.path_params.get("id", "unknown")
        # In a real app this would query a database.
        return RaftResponse.ok(
            message="Item retrieved",
            data={"id": item_id, "name": "Sample", "price": 9.99},
        )

    async def put(self, request: RaftRequest) -> RawResponse:
        item_id = request.path_params.get("id", "unknown")
        updates = await validate_body(request, UpdateItemSchema)
        return RaftResponse.ok(
            message="Item updated",
            data={"id": item_id, **updates.model_dump(exclude_none=True)},
        )


# Register CBV — no .as_view() needed; Route detects the class automatically
app.add_route(Route("/items/{id}", ItemView))


# =========================================================================
# 10. Modular router (Django urlpatterns style)
#     FBVs are registered via add_routes() — no decorator, no as_view().
# =========================================================================

async def list_users(request: RaftRequest) -> RawResponse:
    return RaftResponse.ok(
        message="Users listed",
        data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    )


async def get_user(request: RaftRequest) -> RawResponse:
    user_id = request.path_params["user_id"]
    return RaftResponse.ok(
        message="User retrieved",
        data={"id": user_id, "name": "Alice"},
    )


users_router = Router(prefix="/users")
users_router.add_routes([
    Route("/", list_users, methods=["GET"]),
    Route("/{user_id}", get_user, methods=["GET"]),
])

app.include_router(users_router)


# =========================================================================
# 11. OpenAPI schema + API docs (Swagger UI and ReDoc)
#    Set RAFT_OPENAPI_DOCS_VISIBILITY=public|private in .env
#    If private, set RAFT_OPENAPI_DOCS_PASSWORD.
# =========================================================================

openapi_router = OpenAPIRouter(
    app,
    title="Raft Example API",
    version="0.1.0",
    description="Example API documentation for the Raft Framework",
)
app.include_router(openapi_router.router)


# =========================================================================
# 12. GraphQL endpoint
# =========================================================================

@strawberry.type
class BookType:
    title: str
    author: str


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello from Raft GraphQL!"

    @strawberry.field
    def books(self) -> list[BookType]:
        return [
            BookType(title="Raft in Action", author="Framework Team"),
            BookType(title="Async Python", author="A. Developer"),
        ]


schema = strawberry.Schema(Query)
graphql_router = GraphQLRouter(schema, path="/graphql")
app.include_router(graphql_router.router)


# =========================================================================
# 13. Error demonstration
# =========================================================================

@app.route("/error", methods=["GET"])
async def trigger_error(request: RaftRequest) -> RawResponse:
    """Intentionally raise an HTTPException."""
    raise HTTPException(status_code=418, message="I'm a teapot", errors=["This is a demo error"])


@app.route("/notfound-demo", methods=["GET"])
async def not_found_demo(request: RaftRequest) -> RawResponse:
    """Raise a NotFound exception."""
    raise NotFound(message="The thing you're looking for doesn't exist")
