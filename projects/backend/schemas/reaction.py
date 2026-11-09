"""Reaction and Engagement Pydantic Schemas."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ReactionToggleSchema(BaseModel):
    target_type: str = Field(..., pattern="^(blog|comment)$")
    target_id: int = Field(..., gt=0)


class ReactionResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_type: str
    target_id: int
    liked: bool
    likes_count: int

