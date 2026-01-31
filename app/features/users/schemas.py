"""User request/response schemas."""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


from app.features.subscriptions.schemas import SubscriptionResponse


class UserResponse(UserBase):
    """Schema for user responses."""

    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    subscription: Optional[SubscriptionResponse] = None

    class Config:
        from_attributes = True


# Alias for backward compatibility
User = UserResponse


class UserVerifyRequest(BaseModel):
    """Schema for verifying a user with OTP code."""

    email: EmailStr
    code: str


class DeviceTokenUpdate(BaseModel):
    """Schema for updating user's device registration token."""

    device_reg_token: str
