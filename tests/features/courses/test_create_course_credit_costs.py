import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, patch
from app.features.lessons.models import Lesson
from app.features.users.models import User

@pytest.mark.asyncio
async def test_create_course_saves_credit_costs(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user_data: dict,
):
    """Test that creating a course from an outline saves the lesson credit costs to the database."""
    # Find the current test user
    username = test_user_data["username"]
    result = await db_session.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    assert user is not None

    # Outline payload matching CourseOutline schema
    course_outline_payload = {
        "title": "A Complete Guide to Web Dev",
        "description": "Learn HTML, CSS, and JS",
        "duration": "10 hours",
        "level": "intermediate",
        "outline": [
            {
                "title": "HTML Fundamentals",
                "description": "Basic tags and structure",
                "duration": "2 hours",
                "objectives": ["Understand elements", "Learn nesting"],
                "lessons": [
                    {
                        "title": "Introduction to HTML",
                        "objectives": ["Create first HTML page"],
                        "duration": "30 mins",
                        "credit_cost": 5,
                        "audio_credit_cost": 3,
                        "quiz_credit_cost": 2,
                    },
                    {
                        "title": "Forms and Input",
                        "objectives": ["Handle user input"],
                        "duration": "45 mins",
                        "credit_cost": 10,
                        "audio_credit_cost": 6,
                        "quiz_credit_cost": 4,
                    }
                ]
            }
        ]
    }

    # Patch the background course image generation to avoid external API calls/Firebase issues
    with patch("app.features.courses.service.CourseService.generate_course_image", new_callable=AsyncMock) as mock_gen:
        response = await client.post(
            "/api/v1/courses/create",
            json=course_outline_payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        course_id = data["data"]["id"]

        # Fetch the created lessons from the database to assert credit costs are saved
        result = await db_session.execute(
            select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.order)
        )
        lessons = result.scalars().all()

        assert len(lessons) == 2

        # Assert lesson 1 costs
        assert lessons[0].title == "Introduction to HTML"
        assert lessons[0].credit_cost == 5
        assert lessons[0].audio_credit_cost == 3
        assert lessons[0].quiz_credit_cost == 2

        # Assert lesson 2 costs
        assert lessons[1].title == "Forms and Input"
        assert lessons[1].credit_cost == 10
        assert lessons[1].audio_credit_cost == 6
        assert lessons[1].quiz_credit_cost == 4
