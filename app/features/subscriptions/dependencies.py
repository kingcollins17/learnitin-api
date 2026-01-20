"""Subscription-related dependencies."""

from fastapi import Depends, HTTPException, status
from app.common.deps import get_current_user
from app.features.users.models import User
from .service import SubscriptionService
from .router import get_subscription_service


async def get_premium_user(
    current_user: User = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> User:
    """
    Dependency that ensures the current user has an active premium subscription.
    """
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="User ID not found")

    subscription = await service.get_active_subscription(current_user.id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required",
        )

    return current_user
