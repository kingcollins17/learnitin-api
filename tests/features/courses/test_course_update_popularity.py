import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.models import User
from app.features.courses.models import Course
from app.common.security import get_password_hash, create_access_token
from sqlalchemy import select

@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin (superuser) user."""
    user = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password=get_password_hash("AdminPassword123!"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    """Get authorization headers for admin."""
    token = create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Create a standard active user."""
    user = User(
        email="regular@example.com",
        username="regularuser",
        hashed_password=get_password_hash("UserPassword123!"),
        full_name="Regular User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def regular_headers(regular_user: User) -> dict:
    """Get authorization headers for regular user."""
    token = create_access_token({"sub": str(regular_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_course_update_popularity_score(
    client: AsyncClient,
    db_session: AsyncSession,
    regular_user: User,
    regular_headers: dict,
    admin_headers: dict,
):
    # 1. Create a course owned by the regular user
    course = Course(
        title="Original Course Title",
        description="Original description",
        user_id=regular_user.id,
        duration="5 hours",
        is_public=True,
        popularity_score=10.0,
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    # 2. Regular user tries to update the popularity score
    update_payload = {
        "title": "Updated Title by Regular",
        "popularity_score": 99.0,
    }
    resp = await client.patch(
        f"/api/v1/courses/{course.id}",
        json=update_payload,
        headers=regular_headers,
    )
    assert resp.status_code == 200
    # Field update for title is successful, but popularity_score should be ignored/unchanged (stay 10.0)
    data = resp.json()["data"]
    assert data["title"] == "Updated Title by Regular"
    assert data["popularity_score"] == 10.0

    # 3. Admin user updates the course (updating title and popularity score)
    admin_update_payload = {
        "title": "Updated Title by Admin",
        "popularity_score": 85.5,
    }
    resp = await client.patch(
        f"/api/v1/courses/{course.id}",
        json=admin_update_payload,
        headers=admin_headers,
    )
    assert resp.status_code == 200
    # Both updates should be successful
    data = resp.json()["data"]
    assert data["title"] == "Updated Title by Admin"
    assert data["popularity_score"] == 85.5

    # Verify database persistence
    await db_session.close()
    # Re-fetch course from DB
    result = await db_session.execute(select(Course).where(Course.id == course.id))
    db_course = result.scalar_one()
    assert db_course.popularity_score == 85.5
