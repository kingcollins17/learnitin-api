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
