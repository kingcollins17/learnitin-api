"""Authentication request/response schemas."""
from pydantic import BaseModel


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token payload data."""
    user_id: int | None = None


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str
    password: str
