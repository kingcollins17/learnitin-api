"""Subscription-related dependencies."""

from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.deps import get_current_user, get_async_session
from app.features.users.models import User
from .models import Subscription
from .service import SubscriptionService
from .repository import SubscriptionRepository
from .usage_repository import SubscriptionUsageRepository
from .google_play_service import GooglePlayService


async def get_subscription_service(
    session: AsyncSession = Depends(get_async_session),
) -> SubscriptionService:
    """Dependency to provide SubscriptionService with all repositories."""
    return SubscriptionService(
        repository=SubscriptionRepository(session),
        google_play=GooglePlayService(),
        usage_repository=SubscriptionUsageRepository(session),
    )


async def get_user_subscription(
    current_user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> Subscription:
    """
    Get user's subscription with automatic renewal/demotion logic.

    Flow:
    1. Try to get active subscription
    2. If no active subscription, find any subscription (most recent first)
    3. If premium and expired beyond grace period → demote to free
    4. If free and expired → create new free subscription
    5. If no subscription at all → create free subscription

    Returns:
        The user's current valid subscription.
    """
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="User ID not found")

    now = datetime.now(timezone.utc)

    # Step 1: Try to get active subscription
    subscription = await service.get_active_subscription(current_user.id)

    if subscription:
        # Have active subscription - check if it needs renewal
        if service.is_free_plan(subscription) and now > subscription.expiry_time:
            # Free plan expired - renew it

            subscription = await service.create_free_subscription(current_user.id)
        elif not service.is_free_plan(subscription):
            # Premium subscription - check grace period
            grace_period = timedelta(days=settings.SUBSCRIPTION_GRACE_PERIOD_DAYS)
            expiry_with_grace = subscription.expiry_time + grace_period

            if now > expiry_with_grace:
                # Premium expired beyond grace period - demote to free

                subscription = await service.create_free_subscription(current_user.id)

        return subscription

    # Step 2: No active subscription - check if user has any historical subscription
    any_subscription = await service.repository.get_by_user_id(current_user.id)

    if any_subscription:
        # User has a subscription but it's not active - handle based on type
        if service.is_free_plan(any_subscription):
            # Free plan expired - create new free subscription

            subscription = await service.create_free_subscription(current_user.id)
        else:
            # Premium expired - check grace period
            grace_period = timedelta(days=settings.SUBSCRIPTION_GRACE_PERIOD_DAYS)
            expiry_with_grace = any_subscription.expiry_time + grace_period

            if now > expiry_with_grace:
                # Premium expired beyond grace period - demote to free

                subscription = await service.create_free_subscription(current_user.id)
            else:
                # Still within grace period - return the expired premium
                # (they still have access during grace period)
                subscription = any_subscription

        return subscription

    # Step 3: No subscription at all - create free plan
    subscription = await service.create_free_subscription(current_user.id)
    return subscription


async def get_premium_user(
    current_user: User = Depends(get_current_user),
    subscription: Subscription = Depends(get_user_subscription),
    service: SubscriptionService = Depends(get_subscription_service),
) -> User:
    """
    Dependency that ensures the current user has an active premium subscription.
    """
    if service.is_free_plan(subscription):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required",
        )

    return current_user
