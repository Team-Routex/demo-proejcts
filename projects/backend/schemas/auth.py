"""Authentication and User Profile Pydantic Schemas."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class RegisterSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=150, pattern=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = ""


class LoginSchema(BaseModel):
    identifier: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)


class ProfileUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    website: Optional[str] = None


class AuthorCompactSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    username: str = ""
    name: str = "Author"
    avatar: str = ""


class UserProfileResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: Optional[str] = ""
    bio: Optional[str] = ""
    avatar_url: Optional[str] = ""
    website: Optional[str] = ""
    location: Optional[str] = ""
    twitter_handle: Optional[str] = ""
    github_handle: Optional[str] = ""
    created_at: Optional[datetime] = None


class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str = "user"
    is_verified: bool = False
    is_active: bool = True
    full_name: Optional[str] = ""
    avatar_url: Optional[str] = ""
    bio: Optional[str] = ""
    website: Optional[str] = ""
    stats: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
