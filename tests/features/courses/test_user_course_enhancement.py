"""Tests for UserCourse enhancements."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.models import User
from app.features.courses.models import Course, UserCourse
from app.features.lessons.models import Lesson
from app.features.modules.models import Module

@pytest.mark.asyncio
async def test_user_course_current_lesson(db_session: AsyncSession):
    """Test UserCourse current_lesson_id field."""
    # Setup
    user = User(email="uc_test@example.com", username="uctest", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()
    
    course = Course(title="UC Course", description="Desc", user_id=user.id, duration="1h")
    db_session.add(course)
    await db_session.flush()
    
    module = Module(title="UC Module", course_id=course.id, module_slug="uc-mod", order=1)
    db_session.add(module)
    await db_session.flush()
    
    lesson = Lesson(title="UC Lesson", course_id=course.id, module_id=module.id, order=1)
    db_session.add(lesson)
    await db_session.flush()
    
    # Create UserCourse with current_lesson_id
    user_course = UserCourse(
        user_id=user.id,
        course_id=course.id,
        current_lesson_id=lesson.id
    )
    db_session.add(user_course)
    await db_session.commit()
    await db_session.refresh(user_course)
    
    assert user_course.current_lesson_id == lesson.id
    
    # Update
    user_course.current_lesson_id = None
    db_session.add(user_course)
    await db_session.commit()
    await db_session.refresh(user_course)
    
    assert user_course.current_lesson_id is None


@pytest.mark.asyncio
async def test_update_user_course_lessons_count(db_session: AsyncSession):
    """Test CourseService.update_user_course_lessons_count method."""
    from app.features.courses.service import CourseService
    from app.features.courses.repository import (
        CourseRepository,
        UserCourseRepository,
        CategoryRepository,
        SubCategoryRepository,
    )
    from app.features.modules.repository import ModuleRepository
    from app.features.lessons.repository import LessonRepository
    from unittest.mock import MagicMock
    from app.features.lessons.models import UserLesson
    from app.features.courses.models import ProgressStatus
    from fastapi import HTTPException

    # Setup
    user = User(email="count_test@example.com", username="counttest", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()
    
    course = Course(title="Count Course", description="Desc", user_id=user.id, duration="1h")
    db_session.add(course)
    await db_session.flush()
    
    module = Module(title="Count Module", course_id=course.id, module_slug="count-mod", order=1)
    db_session.add(module)
    await db_session.flush()
    
    lesson1 = Lesson(title="Count Lesson 1", course_id=course.id, module_id=module.id, order=1)
    lesson2 = Lesson(title="Count Lesson 2", course_id=course.id, module_id=module.id, order=2)
    db_session.add(lesson1)
    db_session.add(lesson2)
    await db_session.flush()
    
    # Create UserCourse
    user_course = UserCourse(
        user_id=user.id,
        course_id=course.id,
        total_lessons=0,
        completed_lessons=0,
    )
    db_session.add(user_course)
    await db_session.flush()

    # Create UserLessons
    user_lesson1 = UserLesson(
        user_id=user.id,
        course_id=course.id,
        module_id=module.id,
        lesson_id=lesson1.id,
        status=ProgressStatus.COMPLETED,
    )
    user_lesson2 = UserLesson(
        user_id=user.id,
        course_id=course.id,
        module_id=module.id,
        lesson_id=lesson2.id,
        status=ProgressStatus.IN_PROGRESS,
    )
    db_session.add(user_lesson1)
    db_session.add(user_lesson2)
    await db_session.commit()

    # Instantiate repositories
    course_repo = CourseRepository(db_session)
    module_repo = ModuleRepository(db_session)
    lesson_repo = LessonRepository(db_session)
    user_course_repo = UserCourseRepository(db_session)
    category_repo = CategoryRepository(db_session)
    subcategory_repo = SubCategoryRepository(db_session)

    # Instantiate CourseService
    service = CourseService(
        course_repository=course_repo,
        module_repository=module_repo,
        lesson_repository=lesson_repo,
        user_course_repository=user_course_repo,
        review_repository=MagicMock(),
        category_repository=category_repo,
        subcategory_repository=subcategory_repo,
        storage_service=MagicMock(),
        image_gen_service=MagicMock(),
    )

    # Call update_user_course_lessons_count
    updated_uc = await service.update_user_course_lessons_count(
        user_id=user.id,
        course_id=course.id
    )

    assert updated_uc is not None
    assert updated_uc.total_lessons == 2
    assert updated_uc.completed_lessons == 1

    # Call update_user_course_lessons_count for non-existent enrollment
    with pytest.raises(HTTPException) as exc_info:
        await service.update_user_course_lessons_count(
            user_id=9999,
            course_id=9999
        )
    assert exc_info.value.status_code == 404

