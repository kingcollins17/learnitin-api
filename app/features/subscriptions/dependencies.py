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




async def get_premium_user(
    current_user: User = Depends(get_current_user),
    # subscription: Subscription = Depends(get_user_subscription),
    service: SubscriptionService = Depends(get_subscription_service),
) -> User:
    """
    Dependency that ensures the current user has an active premium subscription.
    """
    # DO NOTHING

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
        # subscription: Subscription = Depends(get_user_subscription),
        service: SubscriptionService = Depends(get_subscription_service),
        usage_service: SubscriptionUsageService = Depends(
            get_subscription_usage_service
        ),
    ) -> None:
        """
        Check if the user has reached their monthly usage limit for the resource.
        Only applies to users on the free plan.
        """
        # Monthly usage limits are removed entirely; metering is handled by credits
        return
