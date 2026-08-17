"""
raft.auth.authentication
~~~~~~~~~~~~~~~~~~~~~~~~

Authentication / permission classes for views.

Authenticate credentials and return ``(user, auth)`` or ``None`` when no
credentials are present. Invalid credentials raise ``Unauthorized``.
"""

from __future__ import annotations

from typing import Any

from raft.auth.jwt import decode_access_token, get_bearer_token
from raft.core.exceptions import Unauthorized
from raft.core.request import RaftRequest


class BaseAuthentication:
    """Base class for authentication backends."""

    def authenticate(self, request: RaftRequest) -> tuple[Any, Any] | None:
        """Return ``(user, auth)`` or ``None`` if this backend does not apply."""
        raise NotImplementedError("authenticate() must be implemented.")


class JWTAuthentication(BaseAuthentication):
    """Authenticate via ``Authorization: Bearer <jwt>``.

    * No Bearer header → ``None`` (anonymous; permissions decide access).
    * Invalid / expired token → ``Unauthorized``.
    * Valid token → ``(claims_dict, raw_token)``.
    """

    www_authenticate_realm = "api"

    def authenticate(self, request: RaftRequest) -> tuple[Any, Any] | None:
        token = get_bearer_token(request)
        if not token:
            return None
        try:
            user = decode_access_token(token)
        except Unauthorized:
            raise
        return user, token

    def authenticate_header(self, request: RaftRequest) -> str:
        return f'Bearer realm="{self.www_authenticate_realm}"'
