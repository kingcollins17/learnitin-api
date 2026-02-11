"""Subscription-related dependencies."""

from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.deps import get_current_user, get_async_session
from app.features.users.models import User
from .models import Subscription, SubscriptionResourceType
from .service import SubscriptionService
from .repository import SubscriptionRepository
from .usage_repository import SubscriptionUsageRepository
from .usage_service import SubscriptionUsageService
from .google_play_service import GooglePlayService


from app.common.dependencies import (
    get_subscription_service,
    get_subscription_usage_service,
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

    now = datetime.now(timezone.utc).replace(tzinfo=None)

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

                subscription = await service.create_free_subscription(
                    current_user.id, dispatch_notification=True
                )

        return subscription

    # Step 2: No active subscription - check if user has any historical subscription
    any_subscription = await service.subscription_repository.get_by_user_id(
        current_user.id
    )

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

                subscription = await service.create_free_subscription(
                    current_user.id, dispatch_notification=True
                )
            else:
                # Still within grace period - return the expired premium
                # (they still have access during grace period)
                subscription = any_subscription

        return subscription

    # Step 3: No subscription at all - create free plan
    subscription = await service.create_free_subscription(
        current_user.id,
        dispatch_notification=False,
    )
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


class ResourceAccessControl:
    """
    Dependency for checking if a user has access to a specific resource
    based on their subscription plan and monthly usage limits.
    """

    def __init__(self, access_resource: SubscriptionResourceType):
        """
        Initialize the dependency with the resource type to check.

        Args:
            access_resource: The resource type (SubscriptionResourceType).
        """
        self.access_resource = access_resource

    async def __call__(
        self,
        subscription: Subscription = Depends(get_user_subscription),
        service: SubscriptionService = Depends(get_subscription_service),
        usage_service: SubscriptionUsageService = Depends(
            get_subscription_usage_service
        ),
    ) -> None:
        """
        Check if the user has reached their monthly usage limit for the resource.
        Only applies to users on the free plan.
        """
        # Premium users (active subscriptions that aren't the free plan) have unlimited access
        if not service.is_free_plan(subscription):
            return

        if not subscription.id:
            # Should not happen with current app architecture, but good to be safe
            return

        # Get current usage via usage service
        usage = await usage_service.get_usage(subscription.id)

        # Check limits based on resource type
        if self.access_resource == SubscriptionResourceType.JOURNEY:
            if (
                usage.learning_journeys_used
                >= settings.FREE_PLAN_LEARNING_JOURNEYS_LIMIT
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Monthly limit for learning journeys reached on Free plan. Upgrade to Premium for unlimited access!",
                )
        elif self.access_resource == SubscriptionResourceType.LESSON:
            if usage.lessons_used >= settings.FREE_PLAN_LESSONS_LIMIT:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Monthly limit for lessons reached on Free plan. Upgrade to Premium for unlimited access!",
                )
        elif self.access_resource == SubscriptionResourceType.AUDIO:
            if usage.audio_lessons_used >= settings.FREE_PLAN_AUDIO_LESSONS_LIMIT:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Monthly limit for audio lessons reached on Free plan. Upgrade to Premium for unlimited access!",
                )
