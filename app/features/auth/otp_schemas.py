from typing import Optional
from pydantic import BaseModel, EmailStr


class OTPRequest(BaseModel):
    """Request schema for OTP generation."""

    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None


class OTPVerify(BaseModel):
    """Request schema for OTP verification."""

    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    code: str


class OTPResponse(BaseModel):
    """Response schema for OTP operations."""

    message: str
    success: bool
