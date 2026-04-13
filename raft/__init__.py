"""
Raft Framework
==============

A Python web framework with hybrid routing, built on ASGI.

Raft provides:
- Hybrid routing (decorator + URL-conf style)
- Function-based and class-based views
- Middleware pipeline (security, CORS, CSRF, XSS, SQLi)
- Pydantic-powered validation
- REST and GraphQL support
- Session management
- Structured JSON responses
- CLI project scaffolding
- Development server with hot reload
- Production-ready uvicorn serving

Quick start::

    from raft import Raft, RaftResponse

    app = Raft()

    @app.route("/hello", methods=["GET"])
    async def hello(request):
        return RaftResponse.ok(message="Hello from Raft!")
"""

from raft.core.app import Raft
from raft.core.response import RaftResponse
from raft.core.request import RaftRequest
from raft.core.router import Router, Route
from raft.core.views import View
from raft.core.exceptions import HTTPException, ValidationError as RaftValidationError
from raft.openapi.router import OpenAPIRouter
from raft.serialization import Serializer, validation_error
from raft.websocket.connection import RaftWebSocket
from raft.websocket.manager import WebSocketManager
from raft.websocket.router import WebSocketRoute

__version__ = "0.1.0"
__all__ = [
    "Raft",
    "RaftResponse",
    "RaftRequest",
    "Router",
    "Route",
    "View",
    "HTTPException",
    "RaftValidationError",
    "OpenAPIRouter",
    "Serializer",
    "validation_error",
    "RaftWebSocket",
    "WebSocketRoute",
    "WebSocketManager",
]
