"""Service for notification business logic."""

from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from .repository import NotificationRepository
from .models import Notification, NotificationType
from .schemas import NotificationCreate, NotificationUpdate
from app.common.events import event_bus, Event, EventType


class NotificationService:
    """Service for notification business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = NotificationRepository(session)

    async def get_user_notifications(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> List[Notification]:
        """Get notifications for a user."""
        return await self.repository.get_by_user(user_id, skip, limit)

    async def get_unread_count(self, user_id: int) -> int:
        """Get unread count for a user."""
        return await self.repository.get_unread_count(user_id)

    async def create_notification(
        self, notification_data: NotificationCreate
    ) -> Notification:
        """Create a notification and trigger in-app push event."""
        notification = Notification(
            user_id=notification_data.user_id,
            title=notification_data.title,
            message=notification_data.message,
            type=notification_data.type,
            data=notification_data.data,
        )

        created_notification = await self.repository.create(notification)

        # Publish event for real-time delivery (WebSocket)
        await event_bus.publish(
            Event(
                type=EventType.NOTIFICATION_IN_APP_PUSH,
                payload={
                    "user_id": created_notification.user_id,
                    "notification_id": created_notification.id,
                    "title": created_notification.title,
                    "message": created_notification.message,
                    "type": created_notification.type,
                    "data": created_notification.data,
                    "created_at": created_notification.created_at.isoformat(),
                },
            )
        )

        return created_notification

    async def mark_as_read(self, notification_id: int, user_id: int) -> Notification:
        """Mark a notification as read."""
        notification = await self.repository.get_by_id(notification_id)

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        if notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this notification",
            )

        notification.is_read = True
        notification.updated_at = datetime.now(timezone.utc)

        return await self.repository.update(notification)

    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        return await self.repository.mark_all_as_read(user_id)

    async def delete_notification(self, notification_id: int, user_id: int) -> None:
        """Delete a notification."""
        notification = await self.repository.get_by_id(notification_id)

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        if notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this notification",
            )

        await self.repository.delete(notification)
