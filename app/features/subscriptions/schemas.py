"""Subscription Pydantic schemas."""

from datetime import datetime
from enum import IntEnum
from typing import Optional
from pydantic import BaseModel
from .models import SubscriptionStatus


class SubscriptionNotificationType(IntEnum):
    """Google Play subscription notification types.

    Reference: https://developer.android.com/google/play/billing/rtdn-reference
    """

    SUBSCRIPTION_RECOVERED = 1  # Subscription recovered from account hold
    SUBSCRIPTION_RENEWED = 2  # Active subscription renewed
    SUBSCRIPTION_CANCELED = 3  # Subscription canceled by user
    SUBSCRIPTION_PURCHASED = 4  # New subscription purchased
    SUBSCRIPTION_ON_HOLD = 5  # Subscription entered account hold (payment issue)
    SUBSCRIPTION_IN_GRACE_PERIOD = 6  # Subscription entered grace period
    SUBSCRIPTION_RESTARTED = 7  # User restarted subscription
    SUBSCRIPTION_PRICE_CHANGE_CONFIRMED = 8  # User confirmed price change
    SUBSCRIPTION_DEFERRED = 9  # Subscription was extended via API
    SUBSCRIPTION_PAUSED = 10  # Subscription paused
    SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED = 11  # Pause schedule changed
    SUBSCRIPTION_REVOKED = 12  # Subscription revoked (refund/chargeback)
    SUBSCRIPTION_EXPIRED = 13  # Subscription expired


class SubscriptionBase(BaseModel):
    """Base subscription schema."""

    product_id: str
    purchase_token: str
    package_name: str


class SubscriptionVerifyRequest(SubscriptionBase):
    """Request schema for subscription verification."""

    pass


class SubscriptionResponse(BaseModel):
    """Response schema for subscription state."""

    id: int
    user_id: int
    product_id: str
    status: SubscriptionStatus
    expiry_time: datetime
    auto_renew: bool
    created_at: datetime
    updated_at: datetime
    usage: Optional["SubscriptionUsageResponse"] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class SubscriptionUsageResponse(BaseModel):
    """Response schema for subscription usage."""

    id: int
    subscription_id: int
    year: int
    month: int
    learning_journeys_used: int
    lessons_used: int
    audio_lessons_used: int

    class Config:
        """Pydantic config."""

        from_attributes = True


# Google Play Pub/Sub notification schemas


class SubscriptionNotification(BaseModel):
    """Typed schema for subscription notification from Google Play."""

    version: Optional[str] = None
    notificationType: Optional[int] = None
    purchaseToken: Optional[str] = None
    subscriptionId: Optional[str] = None


class GooglePlayNotification(BaseModel):
    """Inner data from Google Play Real-Time Developer Notification."""

    version: Optional[str] = None
    packageName: Optional[str] = None
    eventTimeMillis: Optional[str] = None
    subscriptionNotification: Optional[SubscriptionNotification] = None
    oneTimeProductNotification: Optional[dict] = None
    testNotification: Optional[dict] = None


class PubSubMessage(BaseModel):
    """Pub/Sub message wrapper."""

    data: Optional[str] = None  # Base64 encoded JSON
    messageId: Optional[str] = None
    publishTime: Optional[str] = None


class PubSubPayload(BaseModel):
    """Pub/Sub webhook payload envelope."""

    message: Optional[PubSubMessage] = None
    subscription: Optional[str] = None
