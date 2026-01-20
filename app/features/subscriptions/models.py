"""Subscription database models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship


class SubscriptionStatus(str, Enum):
    """Subscription status enum."""

    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"
    PAUSED = "paused"


class Subscription(SQLModel, table=True):
    """Subscription model for database."""

    __tablename__ = "subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, nullable=False)
    product_id: str = Field(max_length=100, nullable=False)
    purchase_token: str = Field(max_length=255, unique=True, index=True, nullable=False)
    status: SubscriptionStatus = Field(index=True, nullable=False)
    expiry_time: datetime = Field(nullable=False)
    auto_renew: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    class Config:
        """Pydantic config."""

        from_attributes = True
