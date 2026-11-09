"""Admin and Telemetry Pydantic Schemas."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AdminOverviewSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_users: int = 0
    total_blogs: int = 0
    total_visits: int = 0
    total_interactions: int = 0
    breakdown: Dict[str, Any] = {}


class AdminBlogListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    summary: Optional[str] = ""
    author: Optional[Dict[str, Any]] = None
    author_username: Optional[str] = ""
    publication_status: str
    approval_status: str
    rejection_reason: Optional[str] = ""
    views_count: int = 0
    likes_count: int = 0
    comments_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AdminUserListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str = ""
    email: str
    role: str = "user"
    is_active: bool = True
    is_verified: bool = False
    avatar_url: Optional[str] = ""
    total_blogs: int = 0
    total_interactions: int = 0
    registration_date: Optional[str] = None
    created_at: Optional[datetime] = None

