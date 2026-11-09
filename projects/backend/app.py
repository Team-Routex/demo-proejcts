"""Raft Blog — Main application entry point.

Follows the canonical RaftFramework architecture (myraft).
Demonstrates all kinds of URL routing:
- Direct app decorators (@app.get)
- Router with prefix and method decorators (@router.get / @router.post)
- Django-style route() tables (routes = [route(...)])
- Class-Based Views (View subclasses with async def get / post / put / delete)
"""

import os
import sys
from pathlib import Path

# Ensure backend directory and framework are on python path
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent.parent

# Set working directory to backend root so setraft.py and relative imports resolve cleanly
os.chdir(BACKEND_DIR)

# Ensure projects/backend is first on sys.path and remove conflicting myraft if present
sys.path = [p for p in sys.path if "myraft" not in p.lower()]
if str(BACKEND_DIR) in sys.path:
    sys.path.remove(str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR))

# Clear any conflicting top-level modules from other scaffolds
for mod_name in list(sys.modules.keys()):
    if mod_name in ("middleware", "models", "routes", "views", "tasks", "commands", "schemas", "ws") or any(
        mod_name.startswith(f"{prefix}.")
        for prefix in ("middleware", "models", "routes", "views", "tasks", "commands", "schemas", "ws")
    ):
        sys.modules.pop(mod_name, None)

if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from raft.config import settings
settings.BASE_DIR = BACKEND_DIR

import raftsql
from raft import Raft, Response
from raft.core.exceptions import NotFound
from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.openapi import OpenAPIRouter
from tasks.scheduler import register_scheduled_tasks
from ws.notifications import register_websocket_routes

# 1. Setup RaftSQL ORM
raftsql.setup()

# 2. Instantiate Raft ASGI application (autodiscovers routes and tasks under BASE_DIR)
app = Raft(debug=True)

# 3. OpenAPI / Swagger / ReDoc
openapi = OpenAPIRouter(app, title="Raft Blog API")
app.include_router(openapi.router)

# ── 1. Direct App Decorator Routing ──────────────────────────────────────────
@app.get("/api/health")
async def health_check(request: RaftRequest) -> Response:
    """Direct application-level decorator routing."""
    return Response.success(data={"status": "healthy", "service": "raft-blog-backend"})


# ── 2. Static Media Serving (Direct App Decorator Routing) ───────────────────
UPLOAD_DIR = BACKEND_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}

@app.get("/uploads/{filename}")
async def serve_upload(request: RaftRequest) -> RawResponse:
    raw_name = request.path_params.get("filename", "")
    safe_name = os.path.basename(raw_name.replace("\\", "/"))
    file_path = UPLOAD_DIR / safe_name
    if not file_path.is_file():
        raise NotFound(message="File not found")

    ext = Path(safe_name).suffix.lower()
    content_type = MIME_TYPES.get(ext, "application/octet-stream")
    body = file_path.read_bytes()
    return RawResponse(body=body, status_code=200, content_type=content_type)

# 4. Periodic background workers (Timed release + 48h auto-approval)
register_scheduled_tasks(app)

# 5. Real-time WebSocket notifications stream
register_websocket_routes(app)
