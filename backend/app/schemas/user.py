from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPreferencesUpdate(BaseModel):
    font_size: Optional[Literal["normal", "large", "larger"]] = None
    display_mode: Optional[Literal["simple", "advanced"]] = None
    reduced_motion: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    font_size: str
    display_mode: str
    reduced_motion: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    sub: Optional[str] = None
