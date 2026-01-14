import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.courses.models import Course, LearningPace, CourseLevel, UserCourse
from app.features.modules.models import Module
from app.features.lessons.models import Lesson
from app.features.users.models import User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_user_course_response_includes_current_position(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    """Test that user course API responses include current_module_id and current_lesson_id."""

    # 1. Get the current user from auth_headers (created by fixture)
    # The auth_headers fixture implicitly creates a user and logs them in.
    # We need to find this user to associate the course/enrollment.
    username = "testuser"  # From conftest.py fixture
    result = await db_session.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    assert user is not None

    # 2. Create a Course
    course = Course(
        title="API Test Course",
        description="Testing API response",
        user_id=user.id,
        duration="1h",
        is_public=True,
    )
    db_session.add(course)
    await db_session.flush()

    # 3. Create Module and Lesson
    module = Module(
        title="Test Module", course_id=course.id, module_slug="test-mod", order=1
    )
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(
        title="Test Lesson", course_id=course.id, module_id=module.id, order=1
    )
    db_session.add(lesson)
    await db_session.flush()

    # 4. Create UserCourse enrollment with current position
    user_course = UserCourse(
        user_id=user.id,
        course_id=course.id,
        current_module_id=module.id,
        current_lesson_id=lesson.id,
    )
    db_session.add(user_course)

    # Update course enrollment count
    course.total_enrollees = 1
    db_session.add(course)

    await db_session.commit()

    # 5. Call user courses API
    response = await client.get("/api/v1/courses/user/courses", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    user_courses = data["data"]["courses"]
    assert len(user_courses) >= 1

    # Find our specific course
    target_enrollment = next(
        (uc for uc in user_courses if uc["course_id"] == course.id), None
    )
    assert target_enrollment is not None

    # Verify new fields are present and correct
    assert "current_module_id" in target_enrollment
    assert "current_lesson_id" in target_enrollment
    assert target_enrollment["current_module_id"] == module.id
    assert target_enrollment["current_lesson_id"] == lesson.id

    # 6. Call user course detail API
    response_detail = await client.get(
        f"/api/v1/courses/user/courses/detail?course_id={course.id}",
        headers=auth_headers,
    )
    assert response_detail.status_code == 200
    data_detail = response_detail.json()

    assert data_detail["status"] == "success"
    user_course_detail = data_detail["data"]

    assert "current_module_id" in user_course_detail
    assert "current_lesson_id" in user_course_detail
    assert user_course_detail["current_module_id"] == module.id
    assert user_course_detail["current_lesson_id"] == lesson.id
