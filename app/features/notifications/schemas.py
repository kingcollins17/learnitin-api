"""Notification request/response schemas."""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import NotificationType


class NotificationBase(BaseModel):
    """Base notification schema."""

    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    data: Optional[Dict[str, Any]] = None


class NotificationCreate(NotificationBase):
    """Schema for creating a notification."""

    user_id: int


class NotificationUpdate(BaseModel):
    """Schema for updating a notification."""

    is_read: Optional[bool] = None


class NotificationResponse(NotificationBase):
    """Schema for notification response."""

    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedNotificationsResponse(BaseModel):
    """Paginated response for notifications."""

    items: List[NotificationResponse]
    total: int
    page: int
    size: int
    pages: int
