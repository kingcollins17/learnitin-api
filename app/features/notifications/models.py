"""Notification database models."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import Field, SQLModel, Column, JSON
from sqlalchemy import Text, Integer, ForeignKey, DateTime
from enum import Enum


class NotificationType(str, Enum):
    """Types of notifications."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SYSTEM = "system"


class Notification(SQLModel, table=True):
    """Notification model for database."""

    __tablename__ = "notifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    title: str = Field(nullable=False)
    message: str = Field(sa_column=Column(Text, nullable=False))
    type: NotificationType = Field(default=NotificationType.INFO, nullable=False)
    is_read: bool = Field(default=False, nullable=False)
    data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Optional[datetime] = Field(default=None)

    class Config:
        """Pydantic config."""

        from_attributes = True
