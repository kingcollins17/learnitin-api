from typing import Optional, Literal
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


class MagicLinkRequest(BaseModel):
    """Request schema for magic link generation."""

    email: EmailStr
    type: Literal["sign_in", "verification"] = "sign_in"
