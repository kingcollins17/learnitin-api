"""Subscription usage service for business logic."""

from typing import Optional
from .models import Subscription, SubscriptionResourceType
from .usage_repository import SubscriptionUsageRepository
from .service import SubscriptionService


class SubscriptionUsageService:
    """Service for managing and tracking subscription usage."""

    def __init__(
        self,
        repository: SubscriptionUsageRepository,
        subscription_service: SubscriptionService,
    ):
        self.repository = repository
        self.subscription_service = subscription_service

    async def increment_usage(
        self,
        subscription: Subscription,
        resource_type: SubscriptionResourceType,
    ) -> None:
        """
        Increment usage for a subscription.

        This is the central point for tracking all subscription-related usage.
        Usage is tracked for ALL plans (free and premium).
        """
        if not subscription.id:
            return

        # Increment usage in repository
        await self.repository.increment_usage(subscription.id, resource_type)

    async def get_usage(self, subscription_id: int):
        """Get current usage for a subscription."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return await self.repository.get_or_create_for_subscription(
            subscription_id, now.year, now.month
        )
