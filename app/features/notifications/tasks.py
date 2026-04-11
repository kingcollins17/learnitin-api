"""Background tasks for notifications."""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.repository import UserRepository
from app.common.dependencies import get_fcm_service
from app.features.notifications.models import Notification

logger = logging.getLogger(__name__)


async def send_push_notification_task(
    user_id: int,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    notification_id: Optional[int] = None,
):
    """
    Background task to send a push notification to a user's device.

    This function creates its own database session to fetch the user's token.
    """
    from app.common.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:

        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)

        if not user or not user.device_reg_token:
            print(
                f"User {user_id} not found or has no device_reg_token. Skipping push notification."
            )
            return

        # FCM data must be strings
        fcm_data = {}
        if data:
            for k, v in data.items():
                fcm_data[k] = str(v)

        if notification_id:
            fcm_data["notification_id"] = str(notification_id)

        # Add common metadata
        fcm_data["click_action"] = "FLUTTER_NOTIFICATION_CLICK"

        print(f"Sending push notification to user {user_id}")
        fcm_service = get_fcm_service()
        response = fcm_service.send_to_token(
            token=user.device_reg_token, title=title, body=body, data=fcm_data
        )

        if response:
            print(f"Push notification sent successfully: {response}")
        else:
            print(f"Failed to send push notification to user {user_id}")


async def send_multicast_push_notification_task(
    user_ids: list[int],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    pre_tokens: Optional[list[str]] = None,
):
    """
    Background task to send a push notification to multiple users via FCM multicast.

    If pre_tokens are provided, skips the DB lookup entirely.
    Otherwise fetches all device tokens in a single DB query, then sends one
    multicast FCM call. Much more efficient than N individual send_to_token calls.
    """
    if pre_tokens:
        # Tokens already provided — skip DB query
        tokens = [t for t in pre_tokens if t]
    else:
        from app.common.database.session import AsyncSessionLocal
        from sqlmodel import select, col
        from app.features.users.models import User

        if not user_ids:
            return

        async with AsyncSessionLocal() as session:
            # Batch-fetch all active users with device tokens
            result = await session.execute(
                select(User)
                .where(col(User.id).in_(user_ids))
                .where(col(User.device_reg_token).isnot(None))
                .where(col(User.is_active) == True)
            )
            users = list(result.scalars().all())
            tokens = [u.device_reg_token for u in users if u.device_reg_token]

    if not tokens:
        logger.info(
            f"No device tokens found for user_ids={user_ids}. Skipping multicast."
        )
        return

    # FCM data must be strings
    fcm_data: Dict[str, str] = {}
    if data:
        for k, v in data.items():
            fcm_data[k] = str(v)
    fcm_data["click_action"] = "FLUTTER_NOTIFICATION_CLICK"

    logger.info(f"Sending multicast push to {len(tokens)} devices")
    fcm_service = get_fcm_service()
    response = fcm_service.send_multicast(
        tokens=tokens, title=title, body=body, data=fcm_data
    )

    if response:
        logger.info(
            f"Multicast result: {response.success_count} success, "
            f"{response.failure_count} failures"
        )
    else:
        logger.warning("Multicast push notification returned no response")
