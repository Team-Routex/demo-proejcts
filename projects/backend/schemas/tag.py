"""Tag Pydantic Schemas for Request Validation and Response Serialization."""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TagCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = None
    description: Optional[str] = ""


class TagUpdateSchema(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None


class TagResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str] = ""
    blog_count: int = 0
    created_at: Optional[datetime] = None

