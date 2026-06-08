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


@pytest.mark.asyncio
async def test_unenroll_course(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    """Test that unenrolling from a course deletes UserCourse, UserModule, and UserLesson progress."""

    # 1. Get current user
    username = "testuser"
    result = await db_session.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    assert user is not None

    # 2. Create Course
    course = Course(
        title="Unenroll Test Course",
        description="Testing unenroll API",
        user_id=user.id,
        duration="1h",
        is_public=True,
    )
    db_session.add(course)
    await db_session.flush()

    # 3. Create Module and Lesson
    module = Module(
        title="Test Module", course_id=course.id, module_slug="unenroll-mod", order=1
    )
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(
        title="Test Lesson", course_id=course.id, module_id=module.id, order=1
    )
    db_session.add(lesson)
    await db_session.flush()

    # 4. Enroll: Create UserCourse, UserModule, UserLesson
    user_course = UserCourse(
        user_id=user.id,
        course_id=course.id,
        current_module_id=module.id,
        current_lesson_id=lesson.id,
    )
    db_session.add(user_course)
    
    from app.features.modules.models import UserModule
    user_module = UserModule(
        user_id=user.id,
        course_id=course.id,
        module_id=module.id,
    )
    db_session.add(user_module)

    from app.features.lessons.models import UserLesson
    user_lesson = UserLesson(
        user_id=user.id,
        course_id=course.id,
        module_id=module.id,
        lesson_id=lesson.id,
    )
    db_session.add(user_lesson)

    course.total_enrollees = 1
    db_session.add(course)
    await db_session.commit()

    # Verify they exist first
    q_uc = await db_session.execute(select(UserCourse).where(UserCourse.user_id == user.id, UserCourse.course_id == course.id))
    assert q_uc.scalar_one_or_none() is not None
    q_um = await db_session.execute(select(UserModule).where(UserModule.user_id == user.id, UserModule.course_id == course.id))
    assert q_um.scalar_one_or_none() is not None
    q_ul = await db_session.execute(select(UserLesson).where(UserLesson.user_id == user.id, UserLesson.course_id == course.id))
    assert q_ul.scalar_one_or_none() is not None

    # 5. Call unenroll API endpoint
    response = await client.post(
        f"/api/v1/courses/{course.id}/unenroll",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["course_id"] == course.id

    # 6. Verify that UserCourse, UserModules, and UserLessons are deleted
    await db_session.commit()
    
    # Check if UserCourse is deleted
    result_uc = await db_session.execute(select(UserCourse).where(UserCourse.user_id == user.id, UserCourse.course_id == course.id))
    assert result_uc.scalar_one_or_none() is None

    # Check if UserModule is deleted
    result_um = await db_session.execute(select(UserModule).where(UserModule.user_id == user.id, UserModule.course_id == course.id))
    assert result_um.scalar_one_or_none() is None

    # Check if UserLesson is deleted
    result_ul = await db_session.execute(select(UserLesson).where(UserLesson.user_id == user.id, UserLesson.course_id == course.id))
    assert result_ul.scalar_one_or_none() is None

    # Check if total_enrollees is decremented to 0
    await db_session.refresh(course)
    assert course.total_enrollees == 0


@pytest.mark.asyncio
async def test_get_user_course_detail_triggers_lessons_count_update(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    """Test that fetching user course detail triggers update of total/completed lessons if null."""
    # 1. Get current user
    username = "testuser"
    result = await db_session.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    assert user is not None

    # 2. Create Course
    course = Course(
        title="Detail Test Course",
        description="Testing detail update API",
        user_id=user.id,
        duration="1h",
        is_public=True,
    )
    db_session.add(course)
    await db_session.flush()

    # 3. Create Module and Lessons
    module = Module(
        title="Test Module", course_id=course.id, module_slug="detail-mod", order=1
    )
    db_session.add(module)
    await db_session.flush()

    lesson1 = Lesson(
        title="Test Lesson 1", course_id=course.id, module_id=module.id, order=1
    )
    lesson2 = Lesson(
        title="Test Lesson 2", course_id=course.id, module_id=module.id, order=2
    )
    db_session.add(lesson1)
    db_session.add(lesson2)
    await db_session.flush()

    # 4. Enroll: Create UserCourse with total_lessons and completed_lessons as None
    user_course = UserCourse(
        user_id=user.id,
        course_id=course.id,
        current_module_id=module.id,
        current_lesson_id=lesson1.id,
        total_lessons=None,
        completed_lessons=None,
    )
    db_session.add(user_course)

    # Create UserLessons progress
    from app.features.lessons.models import UserLesson, ProgressStatus
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

    # 5. Call user course detail API
    response = await client.get(
        f"/api/v1/courses/user/courses/detail?course_id={course.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    user_course_detail = data["data"]

    # Verify that total_lessons and completed_lessons have been updated and are not None
    assert user_course_detail["total_lessons"] == 2
    assert user_course_detail["completed_lessons"] == 1

    # Verify DB has been updated
    await db_session.refresh(user_course)
    assert user_course.total_lessons == 2
    assert user_course.completed_lessons == 1

