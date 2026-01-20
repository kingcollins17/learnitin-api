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


class GoogleWebhookPayload(BaseModel):
    """Schema for Google Play RTDN webhook payload."""

    version: str
    packageName: str
    eventTimeMillis: str
    subscriptionNotification: Optional[dict] = None
    oneTimeProductNotification: Optional[dict] = None
    testNotification: Optional[dict] = None
