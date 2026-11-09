from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BlogCreateSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=10)
    summary: Optional[str] = ""
    featured_image: Optional[str] = ""
    publication_status: Optional[str] = "draft"  # draft | published | scheduled
    scheduled_at: Optional[datetime] = None  # Future timestamp for timed release
    category_ids: Optional[List[int]] = []
    tag_ids: Optional[List[int]] = []


class BlogUpdateSchema(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    featured_image: Optional[str] = None
    publication_status: Optional[str] = None  # draft | published | scheduled
    scheduled_at: Optional[datetime] = None  # Future timestamp for timed release
    category_ids: Optional[List[int]] = None
    tag_ids: Optional[List[int]] = None


class BlogModerationSchema(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    rejection_reason: Optional[str] = ""

