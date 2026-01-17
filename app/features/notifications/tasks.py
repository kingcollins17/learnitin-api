"""Background tasks for notifications."""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.repository import UserRepository
from app.services.fcm_service import firebase_fcm_service
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
            logger.debug(
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

        logger.info(f"Sending push notification to user {user_id}")
        response = firebase_fcm_service.send_to_token(
            token=user.device_reg_token, title=title, body=body, data=fcm_data
        )

        if response:
            logger.info(f"Push notification sent successfully: {response}")
        else:
            logger.warning(f"Failed to send push notification to user {user_id}")
