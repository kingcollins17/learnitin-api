"""Tests for Course model enhancements."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.models import User
from app.features.courses.models import Course, LearningPace, CourseLevel

@pytest.mark.asyncio
async def test_course_enhancements(db_session: AsyncSession):
    """Test Course model fields learning_pace and level."""
    # Create user
    user = User(email="course_test@example.com", username="coursetest", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()
    
    # Create course with new fields
    course = Course(
        user_id=user.id,
        title="Enhanced Course",
        description="Desc",
        duration="1h",
        learning_pace=LearningPace.FAST,
        level=CourseLevel.EXPERT
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)
    
    assert course.learning_pace == LearningPace.FAST
    assert course.level == CourseLevel.EXPERT
    
    # Test defaults
    course_default = Course(
        user_id=user.id,
        title="Default Course",
        description="Desc",
        duration="1h"
    )
    db_session.add(course_default)
    await db_session.commit()
    await db_session.refresh(course_default)
    
    # String comparison because partial loading or enum behavior might be tricky, but direct enum comparison should work
    assert course_default.learning_pace == LearningPace.BALANCED
    assert course_default.level == CourseLevel.BEGINNER
