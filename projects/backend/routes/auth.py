"""Authentication HTTP Route Table."""

from raft import route
from schemas import (
    RegisterSchema,
    LoginSchema,
    ProfileUpdateSchema,
    UserResponseSchema,
)
from views.auth import (
    register_view,
    login_view,
    me_view,
    update_profile_view,
    logout_view,
)

routes = [
    route("/api/auth/register", register_view, methods=["POST"], request_body=RegisterSchema, responses={201: UserResponseSchema}),
    route("/api/auth/login", login_view, methods=["POST"], request_body=LoginSchema, responses={200: UserResponseSchema}),
    route("/api/auth/me", me_view, methods=["GET"], responses={200: UserResponseSchema}),
    route("/api/auth/profile", update_profile_view, methods=["PUT"], request_body=ProfileUpdateSchema, responses={200: UserResponseSchema}),
    route("/api/auth/logout", logout_view, methods=["POST"]),
]
