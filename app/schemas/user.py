from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="Unique username")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password")
    role: Optional[UserRole] = Field(default=UserRole.CONTESTANT, description="Role assigned upon creation")


class UserLogin(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Plaintext password")


class UserUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=0, description="Updated user rating")
    role: Optional[UserRole] = Field(None, description="Updated user role")


class UserResponse(UserBase):
    user_id: int
    rating: int
    role: UserRole
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token string")
    token_type: str = Field(default="bearer", description="Token authentication type")
    expires_in: int = Field(..., description="Token expiration duration in seconds")


class TokenPayload(BaseModel):
    sub: str
    role: UserRole
    exp: int
