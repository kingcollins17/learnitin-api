from typing import Optional
from pydantic import BaseModel, EmailStr


class OTPRequest(BaseModel):
    """Request schema for OTP generation."""

    email: EmailStr


class OTPVerify(BaseModel):
    """Request schema for OTP verification."""

    email: EmailStr
    code: str


class OTPResponse(BaseModel):
    """Response schema for OTP operations."""

    message: str
    success: bool
