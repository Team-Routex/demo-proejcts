from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=150, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = ""


class LoginSchema(BaseModel):
    identifier: str = Field(..., min_length=1)  # username or email
    password: str = Field(..., min_length=6)


class ProfileUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    website: Optional[str] = None

