"""Tests for Lesson model enhancements."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.models import User
from app.features.courses.models import Course
from app.features.modules.models import Module
from app.features.lessons.models import Lesson

@pytest.mark.asyncio
async def test_lesson_has_quiz(db_session: AsyncSession):
    """Test Lesson model field has_quiz."""
    # Setup
    user = User(email="lesson_test@example.com", username="lessontest", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()
    
    course = Course(title="Lesson Course", description="Desc", user_id=user.id, duration="1h")
    db_session.add(course)
    await db_session.flush()
    
    module = Module(title="Lesson Module", course_id=course.id, module_slug="less-mod", order=1)
    db_session.add(module)
    await db_session.flush()
    
    # Create Lesson with has_quiz=True
    lesson = Lesson(
        title="Quiz Lesson", 
        course_id=course.id, 
        module_id=module.id, 
        has_quiz=True
    )
    db_session.add(lesson)
    await db_session.commit()
    await db_session.refresh(lesson)
    
    assert lesson.has_quiz is True
    
    # Test default
    lesson_default = Lesson(
        title="Normal Lesson", 
        course_id=course.id, 
        module_id=module.id
    )
    db_session.add(lesson_default)
    await db_session.commit()
    await db_session.refresh(lesson_default)
    
    assert lesson_default.has_quiz is False
