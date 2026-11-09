"""Pydantic schemas package for Raft Blog application.

Provides request validation models and response serialization schemas.
"""

from typing import Any, List, Union
from pydantic import BaseModel

from schemas.auth import (
    RegisterSchema,
    LoginSchema,
    ProfileUpdateSchema,
    AuthorCompactSchema,
    UserProfileResponseSchema,
    UserResponseSchema,
)
from schemas.category import (
    CategoryCreateSchema,
    CategoryUpdateSchema,
    CategoryResponseSchema,
)
from schemas.tag import (
    TagCreateSchema,
    TagUpdateSchema,
    TagResponseSchema,
)
from schemas.blog import (
    BlogCreateSchema,
    BlogUpdateSchema,
    BlogModerationSchema,
    BlogListItemSchema,
    BlogDetailSchema,
)
from schemas.comment import (
    CommentCreateSchema,
    CommentUpdateSchema,
    CommentResponseSchema,
)
from schemas.reaction import (
    ReactionToggleSchema,
    ReactionResponseSchema,
)
from schemas.notification import (
    NotificationResponseSchema,
)
from schemas.admin import (
    AdminOverviewSchema,
    AdminBlogListItemSchema,
    AdminUserListItemSchema,
)


def dump(obj: Any) -> Any:
    """Helper to dump a Pydantic model, list of models, or dict to JSON-serializable primitives."""
    if obj is None:
        return None
    if isinstance(obj, list):
        return [dump(item) for item in obj]
    if isinstance(obj, dict):
        return {k: dump(v) for k, v in obj.items()}
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


__all__ = [
    "dump",
    "RegisterSchema",
    "LoginSchema",
    "ProfileUpdateSchema",
    "AuthorCompactSchema",
    "UserProfileResponseSchema",
    "UserResponseSchema",
    "CategoryCreateSchema",
    "CategoryUpdateSchema",
    "CategoryResponseSchema",
    "TagCreateSchema",
    "TagUpdateSchema",
    "TagResponseSchema",
    "BlogCreateSchema",
    "BlogUpdateSchema",
    "BlogModerationSchema",
    "BlogListItemSchema",
    "BlogDetailSchema",
    "CommentCreateSchema",
    "CommentUpdateSchema",
    "CommentResponseSchema",
    "ReactionToggleSchema",
    "ReactionResponseSchema",
    "NotificationResponseSchema",
    "AdminOverviewSchema",
    "AdminBlogListItemSchema",
    "AdminUserListItemSchema",
]
