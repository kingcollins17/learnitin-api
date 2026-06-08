import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.models import User
from app.features.courses.models import Category
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
async def standard_user(db_session: AsyncSession) -> User:
    """Create a standard active user."""
    user = User(
        email="user@example.com",
        username="standarduser",
        hashed_password=get_password_hash("UserPassword123!"),
        full_name="Standard User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def custom_auth_headers(standard_user: User) -> dict:
    """Get authorization headers for standard user."""
    token = create_access_token({"sub": str(standard_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_category_crud_restricted_to_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    custom_auth_headers: dict,
    admin_headers: dict,
):
    # Test Create (Non-admin should get 403)
    create_data = {"name": "Test Category Unique", "description": "Category for testing"}
    resp = await client.post("/api/v1/courses/categories", json=create_data, headers=custom_auth_headers)
    assert resp.status_code == 403

    # Test Create (Admin should succeed)
    resp = await client.post("/api/v1/courses/categories", json=create_data, headers=admin_headers)
    assert resp.status_code == 200
    cat_id = resp.json()["data"]["id"]

    # Test Update (Non-admin should get 403)
    update_data = {"name": "Updated Category Unique", "description": "Updated description"}
    resp = await client.patch(
        f"/api/v1/courses/categories/{cat_id}",
        json=update_data,
        headers=custom_auth_headers,
    )
    assert resp.status_code == 403

    # Test Update (Admin should succeed)
    resp = await client.patch(
        f"/api/v1/courses/categories/{cat_id}",
        json=update_data,
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Updated Category Unique"

    # Test Delete (Non-admin should get 403)
    resp = await client.delete(f"/api/v1/courses/categories/{cat_id}", headers=custom_auth_headers)
    assert resp.status_code == 403

    # Test Delete (Admin should succeed)
    resp = await client.delete(f"/api/v1/courses/categories/{cat_id}", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_categories_filterable_search(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict,
):
    # Create test categories
    categories = [
        Category(name="Python Programming Unique", description="Learn Python basics"),
        Category(name="Web Design Unique", description="Introduction to CSS/HTML"),
        Category(name="Cooking Masterclass Unique", description="Chef guides"),
    ]
    for cat in categories:
        db_session.add(cat)
    await db_session.commit()

    # Get all categories without filter (should return 3)
    resp = await client.get("/api/v1/courses/categories")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 3

    # Search for "python"
    resp = await client.get("/api/v1/courses/categories?search=python")
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Filter list manually since there might be other seeded categories in other databases
    filtered = [c for c in data if "Python Programming Unique" in c["name"]]
    assert len(filtered) == 1
    assert filtered[0]["name"] == "Python Programming Unique"

    # Search for "CSS" (in description)
    resp = await client.get("/api/v1/courses/categories?search=CSS")
    assert resp.status_code == 200
    data = resp.json()["data"]
    filtered = [c for c in data if "Web Design Unique" in c["name"]]
    assert len(filtered) == 1
    assert filtered[0]["name"] == "Web Design Unique"

    # Search for non-existent term
    resp = await client.get("/api/v1/courses/categories?search=DoesNotExistUnique")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 0
