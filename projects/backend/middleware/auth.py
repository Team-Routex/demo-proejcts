import hashlib
import hmac
import os
import secrets
from typing import Any, Optional
from raft import create_access_token, decode_access_token, get_bearer_token
from raft.core.exceptions import Unauthorized, Forbidden
from raft.core.request import RaftRequest


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        parts = password_hash.split("$")
        if len(parts) != 3:
            return False
        algo_info, salt, stored_hash = parts
        _, _, iterations_str = algo_info.split(":")
        iterations = int(iterations_str)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(key.hex(), stored_hash)
    except Exception:
        return False


def create_token_for_user(user: Any) -> str:
    user_id = getattr(user, "id", None) or user["id"]
    email = getattr(user, "email", None) or user["email"]
    username = getattr(user, "username", None) or user["username"]
    role = getattr(user, "role", None) or user.get("role", "user")

    claims = {
        "sub": str(user_id),
        "user_id": int(user_id),
        "email": email,
        "username": username,
        "role": role,
    }
    return create_access_token(claims)


def get_authenticated_user(request: RaftRequest, require: bool = True) -> Optional[dict]:
    token = get_bearer_token(request)
    if not token:
        # Check query param (helpful for WebSocket handshakes / downloads)
        token = request.get_query_param("token")

    if not token:
        if require:
            raise Unauthorized(message="Authentication required. Missing Bearer token.")
        return None

    try:
        payload = decode_access_token(token)
        request.user = payload
        request.state["user"] = payload
        return payload
    except Exception as exc:
        if require:
            raise Unauthorized(message=f"Invalid or expired authentication token: {exc}")
        return None


def require_admin(request: RaftRequest) -> dict:
    user = get_authenticated_user(request, require=True)
    if user.get("role") != "admin":
        raise Forbidden(message="Admin privilege required to perform this action.")
    return user

