"""Notification repository for database operations."""

from typing import Optional, List, Tuple
from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .models import Notification


class NotificationRepository:
    """Repository for notification database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, notification_id: int) -> Optional[Notification]:
        """Get notification by ID."""
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Notification]:
        """Get notifications for a specific user."""
        result = await self.session.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_unread_count(self, user_id: int) -> int:
        """Get unread notification count for a user."""
        result = await self.session.execute(
            select(func.count(Notification.id))
            .where(Notification.user_id == user_id)
            .where(Notification.is_read == False)
        )
        return result.scalar_one() or 0

    async def create(self, notification: Notification) -> Notification:
        """Create a new notification."""
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def update(self, notification: Notification) -> Notification:
        """Update an existing notification."""
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        # Using a select then update approach for SQLModel compatibility with async
        result = await self.session.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .where(Notification.is_read == False)
        )
        notifications = result.scalars().all()
        for notification in notifications:
            notification.is_read = True
            self.session.add(notification)

        await self.session.flush()
        return len(notifications)

    async def delete(self, notification: Notification) -> None:
        """Delete a notification."""
        await self.session.delete(notification)
        await self.session.flush()
