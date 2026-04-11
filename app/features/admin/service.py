"""Admin business logic and service layer."""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import select, col

from app.common.service import Commitable
from app.common.events import event_bus, NotificationInAppPushEvent, NotificationMulticastPushEvent
from app.features.users.models import User
from app.features.users.repository import UserRepository
from app.features.users.service import UserService
from app.features.users.schemas import UserResponse
from app.features.courses.models import Course
from app.features.courses.repository import CourseRepository
from app.features.lessons.models import Lesson, LessonAudio
from app.features.lessons.repository import LessonRepository, LessonAudioRepository
from app.features.subscriptions.models import Subscription, SubscriptionStatus
from app.features.subscriptions.service import SubscriptionService
from app.features.subscriptions.schemas import SubscriptionResponse, SubscriptionUsageResponse
from app.features.subscriptions.usage_service import SubscriptionUsageService
from app.features.notifications.service import NotificationService
from app.features.notifications.schemas import NotificationCreate
from app.features.notifications.models import NotificationType
from app.services.storage_service import FirebaseStorageService
from app.services.maintenance_service import DBMaintenanceService
from app.features.admin.schemas import AdminUserListResponse, AdminStatsResponse

logger = logging.getLogger(__name__)


class AdminService(Commitable):
    """Service for admin-level business logic.

    Orchestrates cross-feature operations using existing repositories and services.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        user_service: UserService,
        subscription_service: SubscriptionService,
        subscription_usage_service: "SubscriptionUsageService",
        notification_service: NotificationService,
        course_repository: CourseRepository,
        lesson_repository: LessonRepository,
        lesson_audio_repository: LessonAudioRepository,
        storage_service: FirebaseStorageService,
        maintenance_service: DBMaintenanceService,
    ):
        self.user_repository = user_repository
        self.user_service = user_service
        self.subscription_service = subscription_service
        self.subscription_usage_service = subscription_usage_service
        self.notification_service = notification_service
        self.course_repository = course_repository
        self.lesson_repository = lesson_repository
        self.lesson_audio_repository = lesson_audio_repository
        self.storage_service = storage_service
        self.maintenance_service = maintenance_service

    async def commit_all(self) -> None:
        """Commit all active sessions in the service's repositories."""
        await self.user_repository.session.commit()

    # ========== User Management ==========

    async def list_users(
        self,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
    ) -> AdminUserListResponse:
        """List all users with pagination and multi-dimensional filtering.

        Args:
            page: Page number (1-indexed).
            per_page: Number of items per page.
            search: Optional search query for email, username, or full_name.
            is_active: Filter by active status.
            is_superuser: Filter by superuser status.
            created_after: Filter users created after this datetime.
            created_before: Filter users created before this datetime.

        Returns:
            Paginated user list with metadata.
        """
        session = self.user_repository.session

        # Build base query
        query = select(User)
        count_query = select(func.count()).select_from(User)

        # Text search across email, username, and full_name
        if search:
            search_filter = (
                col(User.email).contains(search)
                | col(User.username).contains(search)
                | col(User.full_name).contains(search)
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Dimensional filters
        if is_active is not None:
            query = query.where(col(User.is_active) == is_active)
            count_query = count_query.where(col(User.is_active) == is_active)

        if is_superuser is not None:
            query = query.where(col(User.is_superuser) == is_superuser)
            count_query = count_query.where(col(User.is_superuser) == is_superuser)

        if created_after is not None:
            query = query.where(col(User.created_at) >= created_after)
            count_query = count_query.where(col(User.created_at) >= created_after)

        if created_before is not None:
            query = query.where(col(User.created_at) <= created_before)
            count_query = count_query.where(col(User.created_at) <= created_before)

        # Get total count
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination
        skip = (page - 1) * per_page
        query = query.order_by(col(User.id).desc()).offset(skip).limit(per_page)

        result = await session.execute(query)
        users = list(result.scalars().all())

        total_pages = math.ceil(total / per_page) if per_page > 0 else 0

        return AdminUserListResponse(
            items=users,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

    async def _get_user_entity(self, user_id: int) -> User:
        """Internal helper to get a User SQLModel entity.

        Args:
            user_id: ID of the user to fetch.

        Returns:
            User entity.

        Raises:
            HTTPException: 404 if user not found.
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def get_user(self, user_id: int) -> UserResponse:
        """Get a single user by ID with detailed subscription and usage info.

        Returns:
            UserResponse with subscription and usage data populated.
        """
        user = await self._get_user_entity(user_id)

        # Map to UserResponse Pydantic model
        user_response = UserResponse.model_validate(user)

        # Fetch active subscription
        subscription = await self.subscription_service.get_active_subscription(user_id)
        if subscription and subscription.id:
            # Attach subscription
            sub_resp = SubscriptionResponse.model_validate(subscription)

            # Fetch usage for this subscription
            usage = await self.subscription_usage_service.get_usage(subscription.id)
            if usage:
                sub_resp.usage = SubscriptionUsageResponse.model_validate(usage)

            user_response.subscription = sub_resp

        return user_response

    async def ban_user(self, user_id: int, reason: Optional[str] = None) -> User:
        """Ban a user by setting is_active to False.

        Args:
            user_id: The user to ban.
            reason: Optional reason for the ban.

        Raises:
            HTTPException: 404 if user not found, 400 if already banned.
        """
        user = await self._get_user_entity(user_id)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already inactive/banned",
            )

        if user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot ban an admin user",
            )

        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        updated_user = await self.user_repository.update(user)

        # Notify user about ban via notification service (persists to DB)
        ban_message = "Your account has been suspended."
        if reason:
            ban_message += f" Reason: {reason}"

        await self.notification_service.create_notification(
            NotificationCreate(
                user_id=user_id,
                title="Account Suspended",
                message=ban_message,
                type="system",
            )
        )

        logger.info(f"Admin banned user {user_id}. Reason: {reason or 'N/A'}")
        return updated_user

    async def unban_user(self, user_id: int) -> User:
        """Unban a user by setting is_active to True.

        Raises:
            HTTPException: 404 if user not found, 400 if already active.
        """
        user = await self._get_user_entity(user_id)

        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already active",
            )

        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)
        updated_user = await self.user_repository.update(user)

        # Notify user about unban
        await self.notification_service.create_notification(
            NotificationCreate(
                user_id=user_id,
                title="Account Restored",
                message="Your account has been reactivated. Welcome back!",
                type="system",
            )
        )

        logger.info(f"Admin unbanned user {user_id}")
        return updated_user

    # ========== Subscription Management ==========

    async def grant_premium(
        self,
        user_id: int,
        duration_days: int = 30,
        product_id: str = "premium_monthly",
    ) -> Subscription:
        """Grant a user premium subscription without Google Play.

        Deactivates existing subscriptions and creates a new ACTIVE subscription
        with the specified duration. Uses the same product_id as Google Play
        purchases so the subscription is indistinguishable from a purchased one.

        Args:
            user_id: Target user.
            duration_days: Subscription duration in days.
            product_id: Google Play product ID (e.g. 'premium_monthly').

        Returns:
            The newly created Subscription.
        """
        # Verify user exists
        await self._get_user_entity(user_id)

        # Deactivate existing subscriptions
        await self.subscription_service.subscription_repository.deactivate_all_for_user(
            user_id
        )

        expiry = (datetime.now(timezone.utc) + timedelta(days=duration_days)).replace(
            tzinfo=None
        )

        sub = Subscription(
            user_id=user_id,
            product_id=product_id,
            purchase_token=None,
            status=SubscriptionStatus.ACTIVE,
            expiry_time=expiry,
            auto_renew=False,
        )

        sub = await self.subscription_service._finalize_and_notify(
            sub,
            title="Premium Granted!",
            message=f"You've been granted {duration_days} days of premium access by an administrator!",
            is_new=True,
            dispatch_notification=False,  # We'll do it via notification_service for persistence
        )

        # Notify via notification service (DB + Push)
        await self.notification_service.create_notification(
            NotificationCreate(
                user_id=user_id,
                title="Premium Activated",
                message=f"You've been granted {duration_days} days of premium access. Enjoy your learning journey!",
                type="system",
                data={"product_id": sub.product_id, "subscription_id": sub.id},
            )
        )

        logger.info(
            f"Admin granted premium to user {user_id} for {duration_days} days"
        )
        return sub

    async def revoke_premium(self, user_id: int) -> Subscription:
        """Revoke premium and revert user to free plan.

        Args:
            user_id: Target user.

        Returns:
            The new free-plan Subscription.
        """
        await self._get_user_entity(user_id)

        sub = await self.subscription_service.create_free_subscription(
            user_id, dispatch_notification=False
        )

        # Notify via notification service
        await self.notification_service.create_notification(
            NotificationCreate(
                user_id=user_id,
                title="Subscription Updated",
                message="Your premium access has been revoked. You are now on the Free plan.",
                type="system",
            )
        )

        logger.info(f"Admin revoked premium for user {user_id}")
        return sub

    # ========== Course Management ==========

    async def list_courses(
        self,
        page: int = 1,
        per_page: int = 20,
        creator_id: Optional[int] = None,
    ) -> dict:
        """List all courses with pagination and optional filters.

        Args:
            page: Page number.
            per_page: Items per page.
            creator_id: Filter by owner/creator ID.

        Returns:
            Dict with items, total, page info.
        """
        session = self.course_repository.session

        # Build query
        query = select(Course)
        count_query = select(func.count()).select_from(Course)

        if creator_id is not None:
            query = query.where(col(Course.user_id) == creator_id)
            count_query = count_query.where(col(Course.user_id) == creator_id)

        # Get total count
        count_result = await session.execute(count_query)
        total = count_result.scalar_one()

        skip = (page - 1) * per_page
        query = query.order_by(col(Course.id).desc()).offset(skip).limit(per_page)

        result = await session.execute(query)
        courses = list(result.scalars().all())

        return {
            "items": courses,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total / per_page) if per_page > 0 else 0,
        }

    async def delete_course(self, course_id: int) -> dict:
        """Delete a course and its associated storage files.

        Cascading deletes will handle modules, lessons, audios in the DB.
        We also attempt to clean up the course image from storage.
        """
        session = self.course_repository.session
        result = await session.execute(
            select(Course).where(col(Course.id) == course_id)
        )
        course = result.scalar_one_or_none()

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Clean up storage for course image
        if course.image_url:
            self.storage_service.delete_file(course.image_url)

        await self.course_repository.delete(course)
        logger.info(f"Admin deleted course {course_id}: {course.title}")

        return {"message": f"Course '{course.title}' deleted successfully"}

    # ========== Audio Management ==========

    async def list_lesson_audios(
        self, lesson_id: int
    ) -> List[LessonAudio]:
        """List all audios for a given lesson."""
        return await self.lesson_audio_repository.get_by_lesson_id(lesson_id)

    async def delete_audio(self, audio_id: int) -> dict:
        """Delete a lesson audio from Firebase Storage and the database.

        Args:
            audio_id: The ID of the audio to delete.

        Returns:
            Confirmation message.
        """
        audio = await self.lesson_audio_repository.get_by_id(audio_id)
        if not audio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio not found",
            )

        # Delete from Firebase Storage
        if audio.audio_url:
            deleted = self.storage_service.delete_file(audio.audio_url)
            if not deleted:
                logger.warning(
                    f"Failed to delete audio file from storage: {audio.audio_url}"
                )

        await self.lesson_audio_repository.delete(audio)
        logger.info(f"Admin deleted audio {audio_id}: {audio.title}")

        return {"message": f"Audio '{audio.title}' deleted successfully"}

    # ========== Notification Management ==========

    async def broadcast_notification(
        self, title: str, message: str, type: NotificationType = NotificationType.INFO
    ) -> dict:
        """Broadcast a notification to all active users via FCM multicast.

        Uses NotificationMulticastPushEvent to send a single batched FCM multicast
        call instead of N individual push events.

        Args:
            title: Notification title.
            message: Notification body.
            type: Notification type.

        Returns:
            Summary of broadcast results.
        """
        session = self.user_repository.session
        result = await session.execute(
            select(User.id).where(col(User.is_active) == True)
        )
        user_ids = [row[0] for row in result.all()]

        if not user_ids:
            return {
                "message": "No active users to broadcast to",
                "sent_count": 0,
            }

        # Dispatch a single multicast event for all users
        await event_bus.dispatch(
            NotificationMulticastPushEvent(
                user_ids=user_ids,
                title=title,
                message=message,
                type=type.value,
            )
        )

        logger.info(f"Admin broadcast notification to {len(user_ids)} users via multicast")
        return {
            "message": f"Notification broadcast to {len(user_ids)} active users",
            "sent_count": len(user_ids),
        }

    async def notify_user(
        self,
        user_id: int,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
    ) -> dict:
        """Send a notification to a single user via bubus event bus.

        Args:
            user_id: Target user ID.
            title: Notification title.
            message: Notification body.
            type: Notification type.
        """
        # Verify user exists
        await self._get_user_entity(user_id)

        await self.notification_service.create_notification(
            NotificationCreate(
                user_id=user_id,
                title=title,
                message=message,
                type=type.value,
            )
        )

        logger.info(f"Admin sent notification to user {user_id}")
        return {"message": f"Notification sent to user {user_id}"}

    async def notify_users(
        self,
        user_ids: List[int],
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
    ) -> dict:
        """Send notifications to a list of users via FCM multicast.

        Uses NotificationMulticastPushEvent for efficient batch delivery.
        Validates user IDs first, then dispatches a single multicast event
        for all valid users.

        Args:
            user_ids: List of target user IDs.
            title: Notification title.
            message: Notification body.
            type: Notification type.
        """
        valid_ids: List[int] = []
        failed_ids: List[int] = []

        for uid in user_ids:
            user = await self.user_repository.get_by_id(uid)
            if not user:
                failed_ids.append(uid)
            else:
                valid_ids.append(uid)

        if valid_ids:
            # Dispatch a single multicast event for all valid users
            await event_bus.dispatch(
                NotificationMulticastPushEvent(
                    user_ids=valid_ids,
                    title=title,
                    message=message,
                    type=type.value,
                )
            )

        logger.info(
            f"Admin sent multicast notification to {len(valid_ids)}/{len(user_ids)} users"
        )
        return {
            "message": f"Notification sent to {len(valid_ids)} users",
            "sent_count": len(valid_ids),
            "failed_user_ids": failed_ids,
        }

    # ========== Platform Stats ==========

    async def get_platform_stats(self) -> AdminStatsResponse:
        """Get high-level platform statistics for the admin dashboard.

        Computes counts for users, courses, lessons, and audio assets.
        """
        # 1. User Stats
        total_users = await self.user_repository.count()
        active_users = await self.user_repository.count(is_active=True)
        total_superusers = await self.user_repository.count(is_superuser=True)

        # 2. Course & Lesson Stats
        total_courses = await self.course_repository.count()
        total_lessons = await self.lesson_repository.count()
        total_audio_lessons = await self.lesson_audio_repository.count()

        return AdminStatsResponse(
            total_users=total_users,
            active_users=active_users,
            total_superusers=total_superusers,
            total_courses=total_courses,
            total_lessons=total_lessons,
            total_audio_lessons=total_audio_lessons,
        )

    # ========== Maintenance ==========

    async def run_maintenance(self) -> dict:
        """Run all database maintenance tasks.

        Returns:
            Results from maintenance operations.
        """
        results = await self.maintenance_service.run_all_maintenance()
        logger.info(f"Admin triggered maintenance: {results}")
        return results
