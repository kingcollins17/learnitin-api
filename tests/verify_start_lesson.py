import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from app.features.courses.models import ProgressStatus
from app.features.lessons.models import UserLesson
from app.features.lessons.service import UserLessonService


@pytest.mark.asyncio
@patch("app.features.lessons.service.UserLessonRepository")
@patch("app.features.lessons.service.LessonRepository")
@patch("app.features.lessons.service.UserModuleRepository")
@patch("app.features.lessons.service.UserModuleService")
@patch("app.features.lessons.service.UserCourseRepository")
async def test_start_lesson_new(
    mock_user_course_repo_cls,
    mock_user_module_service_cls,
    mock_user_module_repo_cls,
    mock_lesson_repo_cls,
    mock_user_lesson_repo_cls,
):
    # Mock instances
    session = AsyncMock()
    mock_user_lesson_repo = AsyncMock()
    mock_lesson_repo = AsyncMock()
    mock_user_module_repo = AsyncMock()
    mock_user_module_service = AsyncMock()
    mock_user_course_repo = AsyncMock()

    mock_user_lesson_repo_cls.return_value = mock_user_lesson_repo
    mock_lesson_repo_cls.return_value = mock_lesson_repo
    mock_user_module_repo_cls.return_value = mock_user_module_repo
    mock_user_module_service_cls.return_value = mock_user_module_service
    mock_user_course_repo_cls.return_value = mock_user_course_repo

    service = UserLessonService(session)

    # Setup mocks
    mock_user_lesson_repo.get_by_user_and_lesson.return_value = None
    mock_user_module_repo.get_by_user_and_module.return_value = (
        MagicMock()
    )  # Module exists
    mock_lesson_repo.get_by_id.return_value = MagicMock(order=1)
    mock_lesson_repo.get_previous_lesson.return_value = None  # No previous lesson

    mock_user_lesson_repo.create.return_value = UserLesson(
        user_id=1,
        lesson_id=10,
        module_id=2,
        course_id=3,
        status=ProgressStatus.IN_PROGRESS,
        is_lesson_unlocked=True,
    )

    result = await service.start_lesson(
        user_id=1, lesson_id=10, module_id=2, course_id=3
    )

    assert result.is_lesson_unlocked == True
    mock_user_lesson_repo.create.assert_called_once()


@pytest.mark.asyncio
@patch("app.features.lessons.service.UserLessonRepository")
@patch("app.features.lessons.service.LessonRepository")
@patch("app.features.lessons.service.UserModuleRepository")
@patch("app.features.lessons.service.UserModuleService")
@patch("app.features.lessons.service.UserCourseRepository")
async def test_start_lesson_existing_locked(
    mock_user_course_repo_cls,
    mock_user_module_service_cls,
    mock_user_module_repo_cls,
    mock_lesson_repo_cls,
    mock_user_lesson_repo_cls,
):
    session = AsyncMock()
    mock_user_lesson_repo = AsyncMock()

    mock_user_lesson_repo_cls.return_value = mock_user_lesson_repo
    # Setup other mocks to return AsyncMock to avoid errors in init
    mock_lesson_repo_cls.return_value = AsyncMock()
    mock_user_module_repo_cls.return_value = AsyncMock()
    mock_user_module_service_cls.return_value = AsyncMock()
    mock_user_course_repo_cls.return_value = AsyncMock()

    service = UserLessonService(session)

    existing_lesson = UserLesson(
        user_id=1,
        lesson_id=10,
        module_id=2,
        course_id=3,
        status=ProgressStatus.IN_PROGRESS,
        is_lesson_unlocked=False,
    )
    mock_user_lesson_repo.get_by_user_and_lesson.return_value = existing_lesson

    result = await service.start_lesson(
        user_id=1, lesson_id=10, module_id=2, course_id=3
    )

    assert result.is_lesson_unlocked == True
    mock_user_lesson_repo.update.assert_called_once()


@pytest.mark.asyncio
@patch("app.features.lessons.service.UserLessonRepository")
@patch("app.features.lessons.service.LessonRepository")
@patch("app.features.lessons.service.UserModuleRepository")
@patch("app.features.lessons.service.UserModuleService")
@patch("app.features.lessons.service.UserCourseRepository")
async def test_start_lesson_existing_unlocked(
    mock_user_course_repo_cls,
    mock_user_module_service_cls,
    mock_user_module_repo_cls,
    mock_lesson_repo_cls,
    mock_user_lesson_repo_cls,
):
    session = AsyncMock()
    mock_user_lesson_repo = AsyncMock()

    mock_user_lesson_repo_cls.return_value = mock_user_lesson_repo
    # Setup other mocks to return AsyncMock to avoid errors in init
    mock_lesson_repo_cls.return_value = AsyncMock()
    mock_user_module_repo_cls.return_value = AsyncMock()
    mock_user_module_service_cls.return_value = AsyncMock()
    mock_user_course_repo_cls.return_value = AsyncMock()

    service = UserLessonService(session)

    existing_lesson = UserLesson(
        user_id=1,
        lesson_id=10,
        module_id=2,
        course_id=3,
        status=ProgressStatus.IN_PROGRESS,
        is_lesson_unlocked=True,
    )
    mock_user_lesson_repo.get_by_user_and_lesson.return_value = existing_lesson

    result = await service.start_lesson(
        user_id=1, lesson_id=10, module_id=2, course_id=3
    )

    assert result.is_lesson_unlocked == True
    mock_user_lesson_repo.update.assert_not_called()
