"""Subscription repository for database operations."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col
from .models import Subscription


class SubscriptionRepository:
    """Repository for subscription database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, subscription_id: int) -> Optional[Subscription]:
        """
        Get a subscription by its primary key ID.

        Args:
            subscription_id: The ID of the subscription to retrieve.

        Returns:
            The `Subscription` object if found, else None.
        """
        result = await self.session.execute(
            select(Subscription).where(col(Subscription.id) == subscription_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> Optional[Subscription]:
        """
        Get the most recent subscription for a given user ID.

        Args:
            user_id: The ID of the user.

        Returns:
            The latest `Subscription` object found in the database.
        """
        # Note: In a real app, a user might have multiple historical subscriptions.
        # For simplicity, we'll get the most recent one.
        result = await self.session.execute(
            select(Subscription)
            .where(col(Subscription.user_id) == user_id)
            .order_by(col(Subscription.expiry_time).desc())
        )
        return result.scalars().first()

    async def get_active_by_user_id(self, user_id: int) -> Optional[Subscription]:
        """
        Retrieve the active subscription for a specific user.

        Only returns subscriptions with ACTIVE status.

        Args:
            user_id: The ID of the user.

        Returns:
            The active `Subscription` if found, else None.
        """
        from .models import SubscriptionStatus

        result = await self.session.execute(
            select(Subscription)
            .where(col(Subscription.user_id) == user_id)
            .where(col(Subscription.status) == SubscriptionStatus.ACTIVE)
            .order_by(col(Subscription.expiry_time).desc())
        )
        return result.scalars().first()

    async def get_by_purchase_token(
        self, purchase_token: str
    ) -> Optional[Subscription]:
        """
        Retrieve a subscription by its unique purchase token.

        Args:
            purchase_token: The Google Play purchase token.

        Returns:
            The `Subscription` object if found, else None.
        """
        result = await self.session.execute(
            select(Subscription)
            .where(col(Subscription.purchase_token) == purchase_token)
            .order_by(col(Subscription.expiry_time).desc())
        )
        return result.scalars().first()

    async def create(self, subscription: Subscription) -> Subscription:
        """Create a new subscription."""
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def update(self, subscription: Subscription) -> Subscription:
        """Update an existing subscription."""
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def deactivate_all_for_user(self, user_id: int) -> int:
        """
        Deactivate all existing subscriptions for a user.

        Sets all subscriptions to EXPIRED status. This should be called
        before creating a new subscription to ensure only one is active.

        Args:
            user_id: The ID of the user.

        Returns:
            The number of subscriptions deactivated.
        """
        from sqlalchemy import update
        from .models import SubscriptionStatus

        result = await self.session.execute(
            update(Subscription)
            .where(col(Subscription.user_id) == user_id)
            .where(col(Subscription.status) == SubscriptionStatus.ACTIVE)
            .values(status=SubscriptionStatus.EXPIRED)
        )
        await self.session.flush()
        return result.rowcount  # type: ignore
