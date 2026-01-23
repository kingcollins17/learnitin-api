"""Subscription usage repository for database operations."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .models import SubscriptionUsage


class SubscriptionUsageRepository:
    """Repository for subscription usage database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_subscription_id(
        self, subscription_id: int
    ) -> Optional[SubscriptionUsage]:
        """
        Get usage record for a specific subscription.

        Args:
            subscription_id: The ID of the subscription.

        Returns:
            The SubscriptionUsage if found, else None.
        """
        result = await self.session.execute(
            select(SubscriptionUsage).where(
                SubscriptionUsage.subscription_id == subscription_id
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_for_subscription(
        self, subscription_id: int, year: int, month: int
    ) -> SubscriptionUsage:
        """
        Get existing usage or create new one for the current period.

        If the existing usage is for a different year/month, reset counters.

        Args:
            subscription_id: The ID of the subscription.
            year: Current UTC year.
            month: Current UTC month.

        Returns:
            The SubscriptionUsage for the current period.
        """
        existing = await self.get_by_subscription_id(subscription_id)

        if existing:
            # Check if we need to reset for a new period
            if existing.year != year or existing.month != month:
                existing.year = year
                existing.month = month
                existing.learning_journeys_used = 0
                existing.lessons_used = 0
                existing.audio_lessons_used = 0
                await self.session.flush()
                await self.session.refresh(existing)
            return existing

        # Create new usage record
        new_usage = SubscriptionUsage(
            subscription_id=subscription_id,
            year=year,
            month=month,
            learning_journeys_used=0,
            lessons_used=0,
            audio_lessons_used=0,
        )
        self.session.add(new_usage)
        await self.session.flush()
        await self.session.refresh(new_usage)
        return new_usage

    async def increment_usage(
        self, subscription_id: int, feature: str
    ) -> SubscriptionUsage:
        """
        Increment usage counter for a specific feature.

        Args:
            subscription_id: The ID of the subscription.
            feature: The feature type ('journey', 'lesson', 'audio').

        Returns:
            The updated SubscriptionUsage.

        Raises:
            ValueError: If the feature is unknown.
        """
        now = datetime.now(timezone.utc)
        usage = await self.get_or_create_for_subscription(
            subscription_id, now.year, now.month
        )

        if feature == "journey":
            usage.learning_journeys_used += 1
        elif feature == "lesson":
            usage.lessons_used += 1
        elif feature == "audio":
            usage.audio_lessons_used += 1
        else:
            raise ValueError(f"Unknown feature: {feature}")

        await self.session.flush()
        await self.session.refresh(usage)
        return usage

    async def create(self, usage: SubscriptionUsage) -> SubscriptionUsage:
        """Create a new usage record."""
        self.session.add(usage)
        await self.session.flush()
        await self.session.refresh(usage)
        return usage

    async def delete_by_subscription_id(self, subscription_id: int) -> None:
        """Delete usage record for a subscription."""
        usage = await self.get_by_subscription_id(subscription_id)
        if usage:
            await self.session.delete(usage)
            await self.session.flush()
