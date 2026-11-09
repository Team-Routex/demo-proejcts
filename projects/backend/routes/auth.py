"""Authentication HTTP Route Table."""

from raft import route
from views.auth import (
    register_view,
    login_view,
    me_view,
    update_profile_view,
    logout_view,
)

routes = [
    route("/api/auth/register", register_view, methods=["POST"]),
    route("/api/auth/login", login_view, methods=["POST"]),
    route("/api/auth/me", me_view, methods=["GET"]),
    route("/api/auth/profile", update_profile_view, methods=["PUT"]),
    route("/api/auth/logout", logout_view, methods=["POST"]),
]
