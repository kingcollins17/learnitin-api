"""User database models."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """User model for database."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    username: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    full_name: Optional[str] = Field(default=None)
    is_active: bool = Field(default=False)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    credits: int = Field(default=0)
    current_plan: Optional[str] = Field(default="free")
    last_subscribed_at: Optional[datetime] = Field(default=None)

    class Config:
        """Pydantic config."""

        from_attributes = True
