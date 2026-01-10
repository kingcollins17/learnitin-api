from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class OTP(SQLModel, table=True):
    """OTP model for database."""

    __tablename__ = "otps"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(default=None, index=True)
    phone_number: Optional[str] = Field(default=None, index=True)
    code: str = Field(nullable=False)
    duration_minutes: int = Field(default=10)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_used: bool = Field(default=False)
