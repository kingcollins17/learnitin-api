"""Tests for admin service layer.

Uses AsyncMock/MagicMock to mock all external dependencies (DB, Firebase, event bus).
"""

import math
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from fastapi import HTTPException

from app.features.admin.service import AdminService
from app.features.admin.schemas import AdminUserListResponse, AdminStatsResponse
from app.features.users.schemas import UserResponse
from app.features.users.models import User
from app.features.courses.models import Course
from app.features.lessons.models import Lesson, LessonAudio
from app.features.subscriptions.models import Subscription, SubscriptionStatus
from app.features.notifications.models import NotificationType
from app.common.events.schemas import NotificationMulticastPushEvent


# ========== Fixtures ==========


@pytest.fixture
def mock_user_repository():
    """Mock user repository."""
    repo = AsyncMock()
    repo.session = AsyncMock()
    return repo


@pytest.fixture
def mock_user_service():
    """Mock user service."""
    return AsyncMock()


@pytest.fixture
def mock_subscription_service():
    """Mock subscription service."""
    svc = AsyncMock()
    svc.subscription_repository = AsyncMock()
    svc.subscription_repository.deactivate_all_for_user = AsyncMock(return_value=1)
    svc._finalize_and_notify = AsyncMock()
    svc.create_free_subscription = AsyncMock()
    return svc


@pytest.fixture
def mock_notification_service():
    """Mock notification service."""
    return AsyncMock()


@pytest.fixture
def mock_course_repository():
    """Mock course repository."""
    repo = AsyncMock()
    repo.session = AsyncMock()
    return repo


@pytest.fixture
def mock_lesson_repository():
    """Mock lesson repository."""
    return AsyncMock()


@pytest.fixture
def mock_lesson_audio_repository():
    """Mock lesson audio repository."""
    return AsyncMock()


@pytest.fixture
def mock_storage_service():
    """Mock Firebase storage service."""
    svc = MagicMock()
    svc.delete_file = MagicMock(return_value=True)
    return svc


@pytest.fixture
def mock_maintenance_service():
    """Mock DB maintenance service."""
    return AsyncMock()


@pytest.fixture
def mock_subscription_usage_service():
    """Mock subscription usage service."""
    svc = AsyncMock()
    svc.get_usage = AsyncMock()
    return svc


@pytest.fixture
def admin_service(
    mock_user_repository,
    mock_user_service,
    mock_subscription_service,
    mock_subscription_usage_service,
    mock_notification_service,
    mock_course_repository,
    mock_lesson_repository,
    mock_lesson_audio_repository,
    mock_storage_service,
    mock_maintenance_service,
):
    """Create AdminService with all mocked dependencies."""
    return AdminService(
        user_repository=mock_user_repository,
        user_service=mock_user_service,
        subscription_service=mock_subscription_service,
        subscription_usage_service=mock_subscription_usage_service,
        notification_service=mock_notification_service,
        course_repository=mock_course_repository,
        lesson_repository=mock_lesson_repository,
        lesson_audio_repository=mock_lesson_audio_repository,
        storage_service=mock_storage_service,
        maintenance_service=mock_maintenance_service,
    )


def _make_user(
    id: int = 1,
    email: str = "test@example.com",
    username: str = "testuser",
    is_active: bool = True,
    is_superuser: bool = False,
) -> User:
    """Helper to create a User model instance."""
    return User(
        id=id,
        email=email,
        username=username,
        is_active=is_active,
        is_superuser=is_superuser,
        created_at=datetime.now(timezone.utc),
    )


def _make_course(id: int = 1, title: str = "Test Course") -> Course:
    """Helper to create a Course model instance."""
    return Course(
        id=id,
        title=title,
        description="A test course",
        duration="4 weeks",
        image_url="https://storage.googleapis.com/bucket/course.png",
        created_at=datetime.now(timezone.utc),
    )


def _make_audio(
    id: int = 1,
    title: str = "Test Audio",
    audio_url: str = "https://storage.googleapis.com/bucket/audio.mp3",
) -> LessonAudio:
    """Helper to create a LessonAudio model instance."""
    return LessonAudio(
        id=id,
        lesson_id=1,
        title=title,
        audio_url=audio_url,
        order=0,
        created_at=datetime.now(timezone.utc),
    )


def _make_subscription(
    id: int = 1,
    user_id: int = 1,
    product_id: str = "premium_monthly",
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
) -> Subscription:
    """Helper to create a Subscription model instance."""
    return Subscription(
        id=id,
        user_id=user_id,
        product_id=product_id,
        status=status,
        expiry_time=datetime.now(timezone.utc) + timedelta(days=30),
        auto_renew=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ========== User Management Tests ==========


@pytest.mark.asyncio
class TestAdminUserManagement:
    """Tests for admin user management operations."""

    async def test_list_users_returns_paginated_response(self, admin_service):
        """list_users should return an AdminUserListResponse with correct pagination."""
        users = [_make_user(id=i, email=f"u{i}@test.com", username=f"user{i}") for i in range(1, 4)]

        # Mock the session.execute for count and query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 3

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = users
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value = mock_scalars

        admin_service.user_repository.session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_query_result]
        )

        result = await admin_service.list_users(page=1, per_page=10)

        assert isinstance(result, AdminUserListResponse)
        assert result.total == 3
        assert result.page == 1
        assert result.per_page == 10
        assert result.total_pages == 1
        assert len(result.items) == 3

    async def test_list_users_with_search(self, admin_service):
        """list_users with search should filter results."""
        users = [_make_user(id=1, email="admin@test.com", username="admin")]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = users
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value = mock_scalars

        admin_service.user_repository.session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_query_result]
        )

        result = await admin_service.list_users(page=1, per_page=10, search="admin")

        assert result.total == 1
        assert len(result.items) == 1
        # Verify execute was called twice (count + data)
        assert admin_service.user_repository.session.execute.call_count == 2

    async def test_list_users_pagination_math(self, admin_service):
        """total_pages should be computed correctly."""
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 25

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value = mock_scalars

        admin_service.user_repository.session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_query_result]
        )

        result = await admin_service.list_users(page=3, per_page=10)

        assert result.total == 25
        assert result.total_pages == 3  # ceil(25/10) = 3
        assert result.page == 3

    async def test_get_user_found(self, admin_service):
        """get_user should return UserResponse with subscription/usage populated."""
        user = _make_user(id=1, email="test@test.com")
        sub = Subscription(
            id=10, 
            user_id=1, 
            product_id="premium_monthly", 
            status=SubscriptionStatus.ACTIVE,
            expiry_time=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        usage_mock = MagicMock(
            id=1, subscription_id=10, year=2024, month=4,
            learning_journeys_used=5, lessons_used=10, audio_lessons_used=3
        )

        admin_service.user_repository.get_by_id = AsyncMock(return_value=user)
        admin_service.subscription_service.get_active_subscription = AsyncMock(return_value=sub)
        admin_service.subscription_usage_service.get_usage = AsyncMock(return_value=usage_mock)

        result = await admin_service.get_user(1)

        assert isinstance(result, UserResponse)
        assert result.id == 1
        assert result.subscription is not None
        assert result.subscription.product_id == "premium_monthly"
        assert result.subscription.usage is not None
        assert result.subscription.usage.lessons_used == 10

    async def test_get_user_found_no_subscription(self, admin_service):
        """get_user should return UserResponse even if no active subscription exists."""
        user = _make_user(id=1)
        admin_service.user_repository.get_by_id = AsyncMock(return_value=user)
        admin_service.subscription_service.get_active_subscription = AsyncMock(return_value=None)

        result = await admin_service.get_user(1)

        assert result.id == 1
        assert result.subscription is None

    async def test_get_user_not_found(self, admin_service):
        """get_user should raise 404 when user doesn't exist."""
        admin_service.user_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await admin_service.get_user(999)
        assert exc_info.value.status_code == 404

    async def test_ban_user_success(self, admin_service):
        """ban_user should deactivate the user and dispatch notification."""
        user = _make_user(id=5, is_active=True)
        admin_service.user_repository.get_by_id = AsyncMock(return_value=user)
        admin_service.user_repository.update = AsyncMock(return_value=user)

        with patch("app.features.admin.service.event_bus") as mock_bus:
            mock_bus.dispatch = AsyncMock()
            result = await admin_service.ban_user(5, reason="Spamming")

        assert result.is_active is False
        mock_bus.dispatch.assert_called_once()

    async def test_ban_user_already_inactive(self, admin_service):
        """ban_user should raise 400 if user is already inactive."""
        user = _make_user(id=5, is_active=False)
        admin_service.user_repository.get_by_id = AsyncMock(return_value=user)

        with pytest.raises(HTTPException) as exc_info:
            await admin_service.ban_user(5)
        assert exc_info.value.status_code == 400
        assert "already inactive" in exc_info.value.detail.lower()

    async def test_ban_admin_user_forbidden(self, admin_service):
        """ban_user should raise 400 when trying to ban a superuser."""
        admin_user = _make_user(id=5, is_active=True, is_superuser=True)
        admin_service.user_repository.get_by_id = AsyncMock(return_value=admin_user)

        with pytest.raises(HTTPException) as exc_info:
            await admin_service.ban_user(5)
        assert exc_info.value.status_code == 400
        assert "admin" in exc_info.value.detail.lower()

    async def test_ban_user_not_found(self, admin_service):
        """ban_user should raise 404 when user doesn't exist."""
        admin_service.user_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await admin_service.ban_user(999)
        assert exc_info.value.status_code == 404

    async def test_unban_user_success(self, admin_service):
        """unban_user should reactivate the user and dispatch notification."""
        user = _make_user(id=5, is_active=False)
        admin_service.user_repository.get_by_id = AsyncMock(return_value=user)
        admin_service.user_repository.update = AsyncMock(return_value=user)

        with patch("app.features.admin.service.event_bus") as mock_bus:
            mock_bus.dispatch = AsyncMock()
            result = await admin_service.unban_user(5)

        assert result.is_active is True
        mock_bus.dispatch.assert_called_once()

    async def test_unban_user_already_active(self, admin_service):
        """unban_user should raise 400 if user is already active."""
        user = _make_user(id=5, is_active=True)
        admin_service.user_repository.get_by_id = AsyncMock(return_value=user)

        with pytest.raises(HTTPException) as exc_info:
            await admin_service.unban_user(5)
        assert exc_info.value.status_code == 400
        assert "already active" in exc_info.value.detail.lower()

    async def test_list_users_filter_by_is_active(self, admin_service):
        """list_users should apply is_active filter."""
        active_users = [_make_user(id=1, is_active=True)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = active_users
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value = mock_scalars

        admin_service.user_repository.session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_query_result]
        )

        result = await admin_service.list_users(page=1, per_page=10, is_active=True)

        assert result.total == 1
        assert len(result.items) == 1
        # Verify execute was called twice (count + data)
        assert admin_service.user_repository.session.execute.call_count == 2

    async def test_list_users_filter_by_is_superuser(self, admin_service):
        """list_users should apply is_superuser filter."""
        admins = [
            _make_user(id=1, email="admin@test.com", username="admin", is_superuser=True)
        ]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = admins
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value = mock_scalars

        admin_service.user_repository.session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_query_result]
        )

        result = await admin_service.list_users(page=1, per_page=10, is_superuser=True)

        assert result.total == 1
        assert len(result.items) == 1

    async def test_list_users_filter_by_date_range(self, admin_service):
        """list_users should apply created_after and created_before filters."""
        users = [_make_user(id=1)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = users
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value = mock_scalars

        admin_service.user_repository.session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_query_result]
        )

        after = datetime(2025, 1, 1, tzinfo=timezone.utc)
        before = datetime(2025, 12, 31, tzinfo=timezone.utc)

        result = await admin_service.list_users(
            page=1, per_page=10, created_after=after, created_before=before
        )

        assert result.total == 1
        assert admin_service.user_repository.session.execute.call_count == 2

    async def test_list_users_combined_filters(self, admin_service):
        """list_users should apply multiple filters simultaneously."""
        users = [_make_user(id=1, email="combo@test.com", username="combo", is_active=True)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = users
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value = mock_scalars

        admin_service.user_repository.session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_query_result]
        )

        result = await admin_service.list_users(
            page=1,
            per_page=10,
            search="combo",
            is_active=True,
            is_superuser=False,
        )

        assert result.total == 1
        assert len(result.items) == 1


# ========== Subscription Management Tests ==========


@pytest.mark.asyncio
class TestAdminSubscriptionManagement:
    """Tests for admin premium subscription operations."""

    async def test_grant_premium_success(self, admin_service):
        """grant_premium should create a new active subscription."""
        user = _make_user(id=10)
        admin_service.user_repository.get_by_id = AsyncMock(return_value=user)

        expected_sub = _make_subscription(user_id=10)
        admin_service.subscription_service._finalize_and_notify = AsyncMock(
            return_value=expected_sub
        )

        result = await admin_service.grant_premium(user_id=10, duration_days=30)

        assert result.user_id == 10
        assert result.status == SubscriptionStatus.ACTIVE

        # Verify deactivation of old subs was called
        admin_service.subscription_service.subscription_repository.deactivate_all_for_user.assert_called_once_with(10)

        # Verify _finalize_and_notify was called with correct args
        call_args = admin_service.subscription_service._finalize_and_notify.call_args
        sub_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("sub")
        assert sub_arg.product_id == "premium_monthly"
        assert sub_arg.auto_renew is False

    async def test_grant_premium_with_custom_product_id(self, admin_service):
        """grant_premium should use the provided product_id (same as Google Play)."""
        user = _make_user(id=10)
        admin_service.user_repository.get_by_id = AsyncMock(return_value=user)

        expected_sub = _make_subscription(user_id=10, product_id="premium_yearly")
        admin_service.subscription_service._finalize_and_notify = AsyncMock(
            return_value=expected_sub
        )

        await admin_service.grant_premium(
            user_id=10, duration_days=365, product_id="premium_yearly"
        )

        call_args = admin_service.subscription_service._finalize_and_notify.call_args
        sub_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("sub")
        assert sub_arg.product_id == "premium_yearly"

    async def test_grant_premium_custom_duration(self, admin_service):
        """grant_premium should use the custom duration."""
        user = _make_user(id=10)
        admin_service.user_repository.get_by_id = AsyncMock(return_value=user)

        expected_sub = _make_subscription(user_id=10)
        admin_service.subscription_service._finalize_and_notify = AsyncMock(
            return_value=expected_sub
        )

        await admin_service.grant_premium(user_id=10, duration_days=90)

        call_args = admin_service.subscription_service._finalize_and_notify.call_args
        sub_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("sub")
        # Check expiry is roughly 90 days from now
        expected_min = datetime.now(timezone.utc) + timedelta(days=89)
        assert sub_arg.expiry_time >= expected_min.replace(tzinfo=None)

    async def test_grant_premium_user_not_found(self, admin_service):
        """grant_premium should raise 404 for nonexistent user."""
        admin_service.user_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await admin_service.grant_premium(user_id=999)
        assert exc_info.value.status_code == 404

    async def test_revoke_premium_success(self, admin_service):
        """revoke_premium should create a free subscription."""
        user = _make_user(id=10)
        admin_service.user_repository.get_by_id = AsyncMock(return_value=user)

        free_sub = _make_subscription(user_id=10, product_id="free")
        admin_service.subscription_service.create_free_subscription = AsyncMock(
            return_value=free_sub
        )

        result = await admin_service.revoke_premium(user_id=10)

        assert result.product_id == "free"
        admin_service.subscription_service.create_free_subscription.assert_called_once_with(
            10, dispatch_notification=True
        )

    async def test_revoke_premium_user_not_found(self, admin_service):
        """revoke_premium should raise 404 for nonexistent user."""
        admin_service.user_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await admin_service.revoke_premium(user_id=999)
        assert exc_info.value.status_code == 404


# ========== Course Management Tests ==========


@pytest.mark.asyncio
class TestAdminCourseManagement:
    """Tests for admin course management operations."""

    async def test_list_courses_paginated(self, admin_service):
        """list_courses should return paginated course data."""
        courses = [_make_course(id=i, title=f"Course {i}") for i in range(1, 4)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 3

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = courses
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value = mock_scalars

        admin_service.course_repository.session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_query_result]
        )

        result = await admin_service.list_courses(page=1, per_page=10)

        assert result["total"] == 3
        assert len(result["items"]) == 3
        assert result["total_pages"] == 1

    async def test_list_courses_with_creator_filter(self, admin_service):
        """list_courses should filter by creator_id."""
        courses = [_make_course(id=1, title="User Course")]
        
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = courses
        mock_query_result = MagicMock()
        mock_query_result.scalars.return_value = mock_scalars
        
        admin_service.course_repository.session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_query_result]
        )
        
        result = await admin_service.list_courses(page=1, per_page=10, creator_id=123)
        
        assert result["total"] == 1
        assert result["items"][0].id == 1
        # Verify execute was called twice (count + data)
        assert admin_service.course_repository.session.execute.call_count == 2

    async def test_delete_course_success(self, admin_service):
        """delete_course should delete from storage and DB."""
        course = _make_course(id=5, title="Stale Course")

        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = course
        admin_service.course_repository.session.execute = AsyncMock(
            return_value=mock_scalar
        )
        admin_service.course_repository.delete = AsyncMock()

        result = await admin_service.delete_course(5)

        assert "deleted" in result["message"].lower()
        admin_service.storage_service.delete_file.assert_called_once_with(
            course.image_url
        )
        admin_service.course_repository.delete.assert_called_once_with(course)

    async def test_delete_course_not_found(self, admin_service):
        """delete_course should raise 404 if course doesn't exist."""
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = None
        admin_service.course_repository.session.execute = AsyncMock(
            return_value=mock_scalar
        )

        with pytest.raises(HTTPException) as exc_info:
            await admin_service.delete_course(999)
        assert exc_info.value.status_code == 404

    async def test_delete_course_no_image(self, admin_service):
        """delete_course should skip storage delete if no image_url."""
        course = _make_course(id=5)
        course.image_url = None

        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = course
        admin_service.course_repository.session.execute = AsyncMock(
            return_value=mock_scalar
        )
        admin_service.course_repository.delete = AsyncMock()

        await admin_service.delete_course(5)

        admin_service.storage_service.delete_file.assert_not_called()
        admin_service.course_repository.delete.assert_called_once()


# ========== Audio Management Tests ==========


@pytest.mark.asyncio
class TestAdminAudioManagement:
    """Tests for admin audio management operations."""

    async def test_list_lesson_audios(self, admin_service):
        """list_lesson_audios should delegate to the audio repository."""
        audios = [_make_audio(id=i, title=f"Audio {i}") for i in range(1, 3)]
        admin_service.lesson_audio_repository.get_by_lesson_id = AsyncMock(
            return_value=audios
        )

        result = await admin_service.list_lesson_audios(lesson_id=1)

        assert len(result) == 2
        admin_service.lesson_audio_repository.get_by_lesson_id.assert_called_once_with(1)

    async def test_delete_audio_success(self, admin_service):
        """delete_audio should delete from Firebase Storage and DB."""
        audio = _make_audio(id=10, title="Old Audio")
        admin_service.lesson_audio_repository.get_by_id = AsyncMock(return_value=audio)
        admin_service.lesson_audio_repository.delete = AsyncMock()

        result = await admin_service.delete_audio(10)

        assert "deleted" in result["message"].lower()
        admin_service.storage_service.delete_file.assert_called_once_with(audio.audio_url)
        admin_service.lesson_audio_repository.delete.assert_called_once_with(audio)

    async def test_delete_audio_not_found(self, admin_service):
        """delete_audio should raise 404 if audio doesn't exist."""
        admin_service.lesson_audio_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await admin_service.delete_audio(999)
        assert exc_info.value.status_code == 404

    async def test_delete_audio_no_url(self, admin_service):
        """delete_audio should skip storage delete if no audio_url."""
        audio = _make_audio(id=10)
        audio.audio_url = None
        admin_service.lesson_audio_repository.get_by_id = AsyncMock(return_value=audio)
        admin_service.lesson_audio_repository.delete = AsyncMock()

        await admin_service.delete_audio(10)

        admin_service.storage_service.delete_file.assert_not_called()
        admin_service.lesson_audio_repository.delete.assert_called_once()

    async def test_delete_audio_storage_failure(self, admin_service):
        """delete_audio should still delete from DB even if storage delete fails."""
        audio = _make_audio(id=10)
        admin_service.lesson_audio_repository.get_by_id = AsyncMock(return_value=audio)
        admin_service.lesson_audio_repository.delete = AsyncMock()
        admin_service.storage_service.delete_file = MagicMock(return_value=False)

        result = await admin_service.delete_audio(10)

        # Should still succeed despite storage failure
        assert "deleted" in result["message"].lower()
        admin_service.lesson_audio_repository.delete.assert_called_once()


# ========== Notification Management Tests ==========


@pytest.mark.asyncio
class TestAdminNotificationManagement:
    """Tests for admin notification operations (broadcast, single, bulk)."""

    async def test_broadcast_notification(self, admin_service):
        """broadcast_notification should dispatch a single multicast event."""
        # Mock session.execute to return user IDs (not full user objects)
        mock_result = MagicMock()
        mock_result.all.return_value = [(1,), (2,), (3,)]
        admin_service.user_repository.session.execute = AsyncMock(
            return_value=mock_result
        )

        with patch("app.features.admin.service.event_bus") as mock_bus:
            mock_bus.dispatch = AsyncMock()
            result = await admin_service.broadcast_notification(
                title="System Update",
                message="New features available!",
                type=NotificationType.INFO,
            )

        assert result["sent_count"] == 3
        # Should dispatch exactly ONE multicast event, not 3 individual events
        mock_bus.dispatch.assert_called_once()
        event_arg = mock_bus.dispatch.call_args.args[0]
        assert isinstance(event_arg, NotificationMulticastPushEvent)
        assert event_arg.user_ids == [1, 2, 3]
        assert event_arg.title == "System Update"

    async def test_broadcast_notification_no_active_users(self, admin_service):
        """broadcast_notification with no active users should not dispatch."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        admin_service.user_repository.session.execute = AsyncMock(
            return_value=mock_result
        )

        with patch("app.features.admin.service.event_bus") as mock_bus:
            mock_bus.dispatch = AsyncMock()
            result = await admin_service.broadcast_notification(
                title="Test", message="Test"
            )

        assert result["sent_count"] == 0
        mock_bus.dispatch.assert_not_called()

    async def test_notify_single_user(self, admin_service):
        """notify_user should dispatch event for the specified user."""
        user = _make_user(id=5)
        admin_service.user_repository.get_by_id = AsyncMock(return_value=user)

        with patch("app.features.admin.service.event_bus") as mock_bus:
            mock_bus.dispatch = AsyncMock()
            result = await admin_service.notify_user(
                user_id=5,
                title="Important",
                message="Your course is ready!",
            )

        assert "5" in result["message"]
        mock_bus.dispatch.assert_called_once()

        # Verify the dispatched event payload
        event_arg = mock_bus.dispatch.call_args.args[0]
        assert event_arg.user_id == 5
        assert event_arg.title == "Important"

    async def test_notify_user_not_found(self, admin_service):
        """notify_user should raise 404 when user doesn't exist."""
        admin_service.user_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await admin_service.notify_user(
                user_id=999, title="Test", message="Test"
            )
        assert exc_info.value.status_code == 404

    async def test_notify_users_bulk(self, admin_service):
        """notify_users should dispatch a single multicast event for valid IDs."""
        users = {
            1: _make_user(id=1, email="a@test.com", username="a"),
            2: _make_user(id=2, email="b@test.com", username="b"),
            3: None,  # User 3 doesn't exist
        }

        async def mock_get_by_id(uid):
            return users.get(uid)

        admin_service.user_repository.get_by_id = AsyncMock(side_effect=mock_get_by_id)

        with patch("app.features.admin.service.event_bus") as mock_bus:
            mock_bus.dispatch = AsyncMock()
            result = await admin_service.notify_users(
                user_ids=[1, 2, 3],
                title="Bulk",
                message="Hello everyone!",
            )

        assert result["sent_count"] == 2
        assert result["failed_user_ids"] == [3]
        # Should dispatch exactly ONE multicast event with valid IDs only
        mock_bus.dispatch.assert_called_once()
        event_arg = mock_bus.dispatch.call_args.args[0]
        assert isinstance(event_arg, NotificationMulticastPushEvent)
        assert event_arg.user_ids == [1, 2]

    async def test_notify_users_all_invalid(self, admin_service):
        """notify_users with all invalid IDs should report all as failed."""
        admin_service.user_repository.get_by_id = AsyncMock(return_value=None)

        with patch("app.features.admin.service.event_bus") as mock_bus:
            mock_bus.dispatch = AsyncMock()
            result = await admin_service.notify_users(
                user_ids=[100, 200],
                title="Test",
                message="Test",
            )

        assert result["sent_count"] == 0
        assert result["failed_user_ids"] == [100, 200]
        mock_bus.dispatch.assert_not_called()

    async def test_notify_users_empty_list(self, admin_service):
        """notify_users with empty list should succeed with 0 sent."""
        with patch("app.features.admin.service.event_bus") as mock_bus:
            mock_bus.dispatch = AsyncMock()
            result = await admin_service.notify_users(
                user_ids=[],
                title="Test",
                message="Test",
            )

        assert result["sent_count"] == 0
        assert result["failed_user_ids"] == []


# ========== Platform Stats Tests ==========


@pytest.mark.asyncio
class TestAdminPlatformStats:
    """Tests for admin platform statistics."""

    async def test_get_platform_stats(self, admin_service):
        """get_platform_stats should return correct aggregate counts."""
        # Mock each count query result
        mock_results = [
            MagicMock(scalar_one=MagicMock(return_value=100)),  # total_users
            MagicMock(scalar_one=MagicMock(return_value=85)),   # active_users
            MagicMock(scalar_one=MagicMock(return_value=5)),    # superusers
            MagicMock(scalar_one=MagicMock(return_value=50)),   # total_courses
            MagicMock(scalar_one=MagicMock(return_value=40)),   # active_courses
            MagicMock(scalar_one=MagicMock(return_value=200)),  # total_lessons
            MagicMock(scalar_one=MagicMock(return_value=180)),  # total_audio_lessons
            MagicMock(scalar_one=MagicMock(return_value=30)),   # total_subs
        ]

        admin_service.user_repository.session.execute = AsyncMock(
            side_effect=mock_results
        )

        result = await admin_service.get_platform_stats()

        assert isinstance(result, AdminStatsResponse)
        assert result.total_users == 100
        assert result.active_users == 85
        assert result.total_superusers == 5
        assert result.total_courses == 50
        assert result.total_active_courses == 40
        assert result.total_lessons == 200
        assert result.total_audio_lessons == 180
        assert result.total_subscriptions == 30

    async def test_get_platform_stats_empty_db(self, admin_service):
        """get_platform_stats should handle empty database (all zeros)."""
        mock_results = [
            MagicMock(scalar_one=MagicMock(return_value=0)) for _ in range(8)
        ]

        admin_service.user_repository.session.execute = AsyncMock(
            side_effect=mock_results
        )

        result = await admin_service.get_platform_stats()

        assert result.total_users == 0
        assert result.total_active_courses == 0
        assert result.total_audio_lessons == 0


# ========== Maintenance Tests ==========


@pytest.mark.asyncio
class TestAdminMaintenance:
    """Tests for admin maintenance operations."""

    async def test_run_maintenance(self, admin_service):
        """run_maintenance should delegate to maintenance service."""
        expected_results = {
            "audios": {"orphans_found": 5, "storage_deleted": 5, "db_deleted": 5},
            "courses": {"orphans_found": 2, "storage_deleted": 2, "db_deleted": 2},
        }
        admin_service.maintenance_service.run_all_maintenance = AsyncMock(
            return_value=expected_results
        )

        result = await admin_service.run_maintenance()

        assert result == expected_results
        admin_service.maintenance_service.run_all_maintenance.assert_called_once()

    async def test_run_maintenance_with_errors(self, admin_service):
        """run_maintenance should propagate error results from the maintenance service."""
        expected_results = {
            "audios": {"error": "Connection timeout"},
            "courses": {"orphans_found": 0, "storage_deleted": 0, "db_deleted": 0},
        }
        admin_service.maintenance_service.run_all_maintenance = AsyncMock(
            return_value=expected_results
        )

        result = await admin_service.run_maintenance()

        assert "error" in result["audios"]


# ========== Commit Tests ==========


@pytest.mark.asyncio
class TestAdminServiceCommit:
    """Tests for the service's commit behavior."""

    async def test_commit_all(self, admin_service):
        """commit_all should commit the user repository session."""
        admin_service.user_repository.session.commit = AsyncMock()

        await admin_service.commit_all()

        admin_service.user_repository.session.commit.assert_called_once()
