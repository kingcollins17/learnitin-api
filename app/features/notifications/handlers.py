"""Event handlers for notifications."""

import logging
import asyncio
from app.common.events import Event, EventType
from .tasks import send_push_notification_task

logger = logging.getLogger(__name__)


async def handle_in_app_push_for_fcm(event: Event):
    """
    Handler for NOTIFICATION_IN_APP_PUSH events.
    Triggers a Firebase Cloud Messaging push notification if the user has a device token.
    """
    payload = event.payload
    user_id = payload.get("user_id")
    title = payload.get("title")
    message = payload.get("message")
    notification_id = payload.get("notification_id")
    data = payload.get("data", {})

    if user_id and title and message:
        # Trigger the push notification task
        # We don't await it here to avoid blocking the event bus worker
        asyncio.create_task(
            send_push_notification_task(
                user_id=int(user_id),
                title=str(title),
                body=str(message),
                data=data,
                notification_id=int(notification_id) if notification_id else None,
            )
        )
