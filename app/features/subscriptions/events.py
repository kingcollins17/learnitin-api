"""Subscription events for Google Play webhook processing."""

from typing import Optional
from app.common.events import AppEvent


class SubscriptionPurchasedEvent(AppEvent):
    """Fired when a new subscription is purchased via Google Play."""

    purchase_token: str
    product_id: str
    package_name: str
    user_id: Optional[int] = None  # May be known from existing token lookup


class SubscriptionRenewedEvent(AppEvent):
    """Fired when a subscription renews automatically."""

    purchase_token: str
    product_id: Optional[str] = None


class SubscriptionCanceledEvent(AppEvent):
    """Fired when a subscription is canceled by user or Google."""

    purchase_token: str


class SubscriptionExpiredEvent(AppEvent):
    """Fired when a subscription expires without renewal."""

    purchase_token: str


class SubscriptionPausedEvent(AppEvent):
    """Fired when a subscription is paused."""

    purchase_token: str


class SubscriptionResumedEvent(AppEvent):
    """Fired when a paused subscription is resumed."""

    purchase_token: str


class SubscriptionRevokedEvent(AppEvent):
    """Fired when a subscription is revoked (refund, chargeback, etc.)."""

    purchase_token: str


class SubscriptionGracePeriodEvent(AppEvent):
    """Fired when subscription enters grace period (payment issue)."""

    purchase_token: str


class SubscriptionRecoveredEvent(AppEvent):
    """Fired when subscription recovers from grace period/account hold."""

    purchase_token: str
