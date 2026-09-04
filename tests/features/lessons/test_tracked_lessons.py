import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.models import User
from app.features.courses.models import Course
from app.features.modules.models import Module
from app.features.lessons.models import Lesson, GenerationType
from app.features.lessons.generation_tracker_service import (
    LessonGenerationTrackerService,
)


@pytest.mark.asyncio
async def test_get_tracked_lessons_endpoint(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    """Test that /lessons/tracked returns active tracked items as detailed Lesson objects."""
    # 1. Get current test user and make them an admin/superuser
    username = "testuser"
    result = await db_session.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    assert user is not None
    user.is_superuser = True
    user.is_active = True
    db_session.add(user)
    await db_session.flush()

    # 2. Create Course, Module, and Lessons in DB
    course = Course(
        title="Test Tracked Course",
        description="For testing tracked endpoint",
        user_id=user.id,
        duration="1h",
        is_public=True,
    )
    db_session.add(course)
    await db_session.flush()

    module = Module(
        title="Test Tracked Module", course_id=course.id, module_slug="tracked-mod", order=1
    )
    db_session.add(module)
    await db_session.flush()

    lesson_audio = Lesson(
        title="Lesson Generating Audio", course_id=course.id, module_id=module.id, order=1
    )
    lesson_content = Lesson(
        title="Lesson Generating Content", course_id=course.id, module_id=module.id, order=2
    )
    db_session.add(lesson_audio)
    db_session.add(lesson_content)
    await db_session.commit()

    # Verify initial tracked endpoint returns empty lists
    response = await client.get("/api/v1/lessons/tracked", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["audio_generation"] == []
    assert data["data"]["content_generation"] == []

    # Start tracking the created lessons
    tracker_service = LessonGenerationTrackerService(db_session)
    await tracker_service.start_tracking(
        user_id=user.id, lesson_id=lesson_audio.id, generation_type=GenerationType.AUDIO
    )
    await tracker_service.start_tracking(
        user_id=user.id, lesson_id=lesson_content.id, generation_type=GenerationType.CONTENT
    )
    await db_session.commit()

    # Verify endpoint returns the tracked lessons from database with full details
    response = await client.get("/api/v1/lessons/tracked", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    audio_gen_list = data["data"]["audio_generation"]
    content_gen_list = data["data"]["content_generation"]

    assert len(audio_gen_list) == 1
    assert audio_gen_list[0]["id"] == lesson_audio.id
    assert audio_gen_list[0]["title"] == "Lesson Generating Audio"

    assert len(content_gen_list) == 1
    assert content_gen_list[0]["id"] == lesson_content.id
    assert content_gen_list[0]["title"] == "Lesson Generating Content"

    # Stop tracking
    await tracker_service.complete_tracking(
        generation_type=GenerationType.AUDIO, lesson_id=lesson_audio.id
    )
    await tracker_service.complete_tracking(
        generation_type=GenerationType.CONTENT, lesson_id=lesson_content.id
    )
    await db_session.commit()

    # Verify they are cleared
    response = await client.get("/api/v1/lessons/tracked", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["audio_generation"] == []
    assert data["data"]["content_generation"] == []

