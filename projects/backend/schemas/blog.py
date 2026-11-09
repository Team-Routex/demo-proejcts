"""Blog Post Pydantic Schemas for Requests and Responses."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from schemas.auth import AuthorCompactSchema
from schemas.category import CategoryResponseSchema
from schemas.tag import TagResponseSchema


class BlogCreateSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=10)
    summary: Optional[str] = ""
    featured_image: Optional[str] = ""
    publication_status: Optional[str] = "draft"  # draft | published | scheduled
    scheduled_at: Optional[datetime] = None
    category_ids: Optional[List[int]] = []
    tag_ids: Optional[List[int]] = []


class BlogUpdateSchema(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    featured_image: Optional[str] = None
    publication_status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    category_ids: Optional[List[int]] = None
    tag_ids: Optional[List[int]] = None


class BlogModerationSchema(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    rejection_reason: Optional[str] = ""


class BlogListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    summary: Optional[str] = ""
    featured_image: Optional[str] = ""
    views_count: int = 0
    likes_count: int = 0
    comments_count: int = 0
    publication_status: str = "draft"
    approval_status: str = "pending"
    rejection_reason: Optional[str] = ""
    scheduled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    author: Optional[AuthorCompactSchema] = None
    categories: List[CategoryResponseSchema] = []
    tags: List[TagResponseSchema] = []


class BlogDetailSchema(BlogListItemSchema):
    content: str
    has_liked: bool = False
    is_liked: bool = False
    is_bookmarked: bool = False
