"""Comment Pydantic Schemas for Requests and Responses."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CommentCreateSchema(BaseModel):
    content: str = Field(..., min_length=1)
    parent_id: Optional[int] = None


class CommentUpdateSchema(BaseModel):
    content: str = Field(..., min_length=1)


class CommentResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    blog_id: int
    parent_id: Optional[int] = None
    content: str
    is_approved: bool = True
    likes_count: int = 0
    user_has_liked: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    author: Optional[Dict[str, Any]] = None
    replies: List[Dict[str, Any]] = []

