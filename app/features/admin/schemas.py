"""Admin request/response schemas."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.features.users.schemas import UserResponse
from app.features.notifications.models import NotificationType


# ========== User Management ==========


class AdminUserListResponse(BaseModel):
    """Paginated user list response for admin."""

    items: List[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class AdminBanUserRequest(BaseModel):
    """Request schema for banning a user."""

    reason: Optional[str] = None


class AdminGrantPremiumRequest(BaseModel):
    """Request schema for granting premium subscription.

    The product_id should match a real Google Play product ID
    (e.g. 'premium_monthly') so the subscription behaves identically
    to a Google Play purchase.
    """

    duration_days: int = 30
    product_id: str


# ========== Notification Management ==========


class AdminBroadcastNotificationRequest(BaseModel):
    """Request schema for broadcasting a notification to all users."""

    title: str
    message: str
    type: NotificationType = NotificationType.INFO


class AdminNotifyUserRequest(BaseModel):
    """Request schema for notifying a single user."""

    user_id: int
    title: str
    message: str
    type: NotificationType = NotificationType.INFO


class AdminNotifyUsersRequest(BaseModel):
    """Request schema for notifying a list of users."""

    user_ids: List[int]
    title: str
    message: str
    type: NotificationType = NotificationType.INFO


# ========== Platform Stats ==========


class AdminStatsResponse(BaseModel):
    """Response schema for platform statistics."""

    total_users: int
    active_users: int
    total_superusers: int
    total_courses: int
    total_active_courses: int
    total_lessons: int
    total_audio_lessons: int
    total_subscriptions: int
