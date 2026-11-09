"""Notification Pydantic Schemas."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class NotificationResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    message: str
    target_id: Optional[int] = None
    target_slug: Optional[str] = None
    is_read: bool = False
    created_at: Optional[datetime] = None
    sender: Optional[Dict[str, Any]] = None

