"""Subscription database models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy import ForeignKey, Integer


class SubscriptionStatus(str, Enum):
    """Subscription status enum."""

    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"
    PAUSED = "paused"


class SubscriptionResourceType(str, Enum):
    """Resource types tracked by subscriptions."""

    JOURNEY = "journeys"
    LESSON = "lessons"
    AUDIO = "audio"


class Subscription(SQLModel, table=True):
    """Subscription model for database."""

    __tablename__ = "subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    product_id: str = Field(max_length=100, nullable=False)
    purchase_token: Optional[str] = Field(
        default=None, max_length=255, index=True, nullable=True
    )
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


class SubscriptionUsage(SQLModel, table=True):
    """Usage tracking with 1:1 relationship to Subscription.

    Tracks per-subscription monthly usage (NOT directly tied to user).
    The unique constraint on subscription_id enforces one-to-one relationship.
    """

    __tablename__ = "subscription_usages"

    id: Optional[int] = Field(default=None, primary_key=True)
    subscription_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("subscriptions.id", ondelete="CASCADE"),
            unique=True,
            index=True,
            nullable=False,
        )
    )
    year: int = Field(nullable=False)
    month: int = Field(nullable=False)
    learning_journeys_used: int = Field(default=0)
    lessons_used: int = Field(default=0)
    audio_lessons_used: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    class Config:
        """Pydantic config."""

        from_attributes = True
