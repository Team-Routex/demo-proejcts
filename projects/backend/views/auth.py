"""Authentication and User Profile Views."""

import re
from raft import Response
from raft.core.exceptions import HTTPException, ValidationError, NotFound
from raft.core.request import RaftRequest
from models.user import User, UserProfile
from models.blog import Blog
from middleware.auth import (
    hash_password,
    verify_password,
    create_token_for_user,
    get_authenticated_user,
)
from schemas import (
    RegisterSchema,
    LoginSchema,
    ProfileUpdateSchema,
    UserResponseSchema,
    UserProfileResponseSchema,
    dump,
)


def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


async def register_view(request: RaftRequest) -> Response:
    """Register a new user account with profile."""
    data = await request.json() or {}
    username = str(data.get("username", "")).strip().lower()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()
    full_name = str(data.get("full_name", "")).strip()

    errors = []
    if not username or len(username) < 3:
        errors.append("Username must be at least 3 characters long.")
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        errors.append("Username may only contain letters, numbers, underscores, and dashes.")
    if not email or not _validate_email(email):
        errors.append("A valid email address is required.")
    if not password or len(password) < 6:
        errors.append("Password must be at least 6 characters long.")

    if errors:
        raise ValidationError(message="Validation failed", errors=errors)

    if await User.objects.filter(username=username).aexists():
        raise HTTPException(status_code=409, message="Username is already taken.")
    if await User.objects.filter(email=email).aexists():
        raise HTTPException(status_code=409, message="Email address is already registered.")

    hashed = hash_password(password)
    user = await User.objects.acreate(
        username=username,
        email=email,
        password_hash=hashed,
        role="user",
        is_verified=False,
        is_active=True,
    )

    profile = await UserProfile.objects.acreate(
        user_id=user.id,
        full_name=full_name or username.capitalize(),
        bio="",
        avatar_url="",
        website="",
    )

    token = create_token_for_user(user)

    user_schema = UserResponseSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_verified=user.is_verified,
        is_active=user.is_active,
        full_name=profile.full_name,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        website=profile.website,
        created_at=user.created_at,
    )

    return Response.created(
        data={"user": dump(user_schema), "token": token, "token_type": "bearer"},
        message="Registration successful.",
    )


async def login_view(request: RaftRequest) -> Response:
    """Authenticate credentials and return bearer JWT token."""
    data = await request.json() or {}
    identifier = str(data.get("identifier", data.get("email", data.get("username", "")))).strip().lower()
    password = str(data.get("password", "")).strip()

    if not identifier or not password:
        raise ValidationError(message="Email or username and password are required.")

    user = None
    if "@" in identifier:
        user = await User.objects.filter(email=identifier).afirst()
    else:
        user = await User.objects.filter(username=identifier).afirst()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, message="Invalid email/username or password.")

    if not user.is_active:
        raise HTTPException(status_code=403, message="This account has been deactivated. Please contact support.")

    profile = await UserProfile.objects.filter(user_id=user.id).afirst()
    token = create_token_for_user(user)

    user_schema = UserResponseSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_verified=user.is_verified,
        is_active=user.is_active,
        full_name=profile.full_name if profile else user.username,
        avatar_url=profile.avatar_url if profile else "",
        bio=profile.bio if profile else "",
        website=profile.website if profile else "",
        created_at=user.created_at,
    )

    return Response.success(
        data={"user": dump(user_schema), "token": token, "token_type": "bearer"},
        message="Login successful.",
    )


async def me_view(request: RaftRequest) -> Response:
    """Retrieve currently authenticated user and telemetry."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]

    user = await User.objects.filter(id=user_id).afirst()
    if not user:
        raise NotFound(message="User not found.")

    profile = await UserProfile.objects.filter(user_id=user.id).afirst()

    total_blogs = await Blog.objects.filter(author_id=user.id).acount()
    approved_blogs = await Blog.objects.filter(author_id=user.id, approval_status="approved").acount()
    pending_blogs = await Blog.objects.filter(author_id=user.id, approval_status="pending").acount()
    rejected_blogs = await Blog.objects.filter(author_id=user.id, approval_status="rejected").acount()
    draft_blogs = await Blog.objects.filter(author_id=user.id, publication_status="draft").acount()

    stats = {
        "total_blogs": total_blogs,
        "approved_blogs": approved_blogs,
        "pending_blogs": pending_blogs,
        "rejected_blogs": rejected_blogs,
        "draft_blogs": draft_blogs,
    }

    user_schema = UserResponseSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_verified=user.is_verified,
        is_active=user.is_active,
        full_name=profile.full_name if profile else user.username,
        avatar_url=profile.avatar_url if profile else "",
        bio=profile.bio if profile else "",
        website=profile.website if profile else "",
        stats=stats,
        created_at=user.created_at,
    )

    return Response.success(data={"user": dump(user_schema), "stats": stats})


async def update_profile_view(request: RaftRequest) -> Response:
    """Update profile information for the authenticated user."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]

    profile = await UserProfile.objects.filter(user_id=user_id).afirst()
    if not profile:
        profile = await UserProfile.objects.acreate(user_id=user_id)

    data = await request.json() or {}
    if "full_name" in data:
        profile.full_name = str(data["full_name"]).strip()
    if "bio" in data:
        profile.bio = str(data["bio"]).strip()
    if "avatar_url" in data:
        profile.avatar_url = str(data["avatar_url"]).strip()
    if "website" in data:
        profile.website = str(data["website"]).strip()

    await profile.asave()

    profile_schema = UserProfileResponseSchema(
        full_name=profile.full_name or "",
        bio=profile.bio or "",
        avatar_url=profile.avatar_url or "",
        website=profile.website or "",
        location=getattr(profile, "location", "") or "",
        twitter_handle=getattr(profile, "twitter_handle", "") or "",
        github_handle=getattr(profile, "github_handle", "") or "",
        created_at=profile.created_at,
    )

    return Response.success(
        data=dump(profile_schema),
        message="Profile updated successfully.",
    )


async def logout_view(request: RaftRequest) -> Response:
    """Terminate the client session."""
    return Response.success(message="Logged out successfully.")
