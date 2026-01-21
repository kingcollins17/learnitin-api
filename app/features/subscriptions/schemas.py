"""Subscription Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from .models import SubscriptionStatus


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

    class Config:
        """Pydantic config."""

        from_attributes = True


# 1. This matches the inner data from Google Play
class GooglePlayNotification(BaseModel):
    version: Optional[str] = None
    packageName: Optional[str] = None
    eventTimeMillis: Optional[str] = None
    subscriptionNotification: Optional[dict] = None
    oneTimeProductNotification: Optional[dict] = None
    testNotification: Optional[dict] = None


# 2. This matches the "Envelope" that Pub/Sub sends to your webhook
class PubSubMessage(BaseModel):
    data: Optional[str] = None  # This is the Base64 string
    messageId: Optional[str] = None
    publishTime: Optional[str] = None


class PubSubPayload(BaseModel):
    message: Optional[PubSubMessage] = None
    subscription: Optional[str] = None
