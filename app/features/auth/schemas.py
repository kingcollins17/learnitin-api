"""Authentication request/response schemas."""

from pydantic import BaseModel


class Token(BaseModel):
    """
    Token response schema for login endpoint.

    Contains the JWT access token and user information. Clients should check
    the is_active field to determine if the user needs to verify their account.
    """

    access_token: str
    token_type: str
    user_id: int
    email: str
    username: str
    is_active: bool


class TokenData(BaseModel):
    """Token payload data."""

    user_id: int | None = None


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str
    password: str
