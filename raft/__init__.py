"""
Raft Framework
==============

A Python web framework with hybrid routing, built on ASGI.

Raft provides:
- Hybrid routing (decorator + URL-conf style)
- Function-based and class-based views
- Middleware pipeline (security, CORS, CSRF, XSS, SQLi)
- REST APIs
- Session management
- Structured JSON responses
- CLI project scaffolding
- Development server with hot reload
- Production-ready uvicorn serving

Quick start::

    from raft import Raft, Response

    app = Raft()

    @app.get("/hello")
    async def hello(request):
        return Response.success(message="Hello from Raft!")
"""

from raft.core.app import Raft
from raft.core.response import Response
from raft.core.request import RaftRequest
from raft.core.router import Router, Route, include, route
from raft.core.views import View
from raft.core.exceptions import HTTPException, ValidationError as RaftValidationError
from raft.openapi.router import OpenAPIRouter
from raft.auth import (
    AllowAny,
    BaseAuthentication,
    BasePermission,
    IsAuthenticated,
    JWTAuthentication,
    authentication_classes,
    create_access_token,
    decode_access_token,
    get_bearer_token,
    jwt_auth_middleware,
    permission_classes,
    require_auth,
)
from raft.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    get_circuit,
    reset_circuits,
)
from raft.redis import get_redis, redis_configured, redis_key
from raft.websocket.connection import RaftWebSocket
from raft.websocket.manager import WebSocketManager
from raft.websocket.router import WebSocketRoute

__version__ = "0.1.0"
__all__ = [
    "Raft",
    "Response",
    "RaftRequest",
    "Router",
    "Route",
    "route",
    "include",
    "View",
    "HTTPException",
    "RaftValidationError",
    "OpenAPIRouter",
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "get_circuit",
    "reset_circuits",
    "create_access_token",
    "decode_access_token",
    "get_bearer_token",
    "require_auth",
    "jwt_auth_middleware",
    "JWTAuthentication",
    "BaseAuthentication",
    "IsAuthenticated",
    "AllowAny",
    "BasePermission",
    "authentication_classes",
    "permission_classes",
    "get_redis",
    "redis_configured",
    "redis_key",
    "RaftWebSocket",
    "WebSocketRoute",
    "WebSocketManager",
]
