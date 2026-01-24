"""Event handlers for notifications."""

import logging
import asyncio
from app.common.events import NotificationInAppPushEvent
from .tasks import send_push_notification_task

logger = logging.getLogger(__name__)


async def handle_in_app_push_for_fcm(event: NotificationInAppPushEvent):
    """
    Handler for NOTIFICATION_IN_APP_PUSH events.
    Triggers a Firebase Cloud Messaging push notification if the user has a device token.
    """
    print("Handling in app push for FCM")
    user_id = event.user_id
    title = event.title
    message = event.message
    notification_id = event.notification_id
    data = event.data or {}
    if event.in_app_event:
        data["in_app_event"] = event.in_app_event.value

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
