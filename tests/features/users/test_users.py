"""Tests for users feature."""
import pytest
from httpx import AsyncClient


@pytest.mark.users
@pytest.mark.asyncio
class TestUserRead:
    """Test reading user information."""
    
    async def test_get_current_user(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_user_data: dict
    ):
        """Test getting current user information."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["full_name"] == test_user_data["full_name"]
        assert data["is_active"] is True
        assert "hashed_password" not in data
    
    async def test_get_user_by_id(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        created_user: dict
    ):
        """Test getting user by ID."""
        user_id = created_user["id"]
        response = await client.get(
            f"/api/v1/users/{user_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == created_user["email"]
    
    async def test_get_user_unauthorized(self, client: AsyncClient):
        """Test that getting user without auth fails."""
        response = await client.get("/api/v1/users/me")
        
        assert response.status_code == 401
    
    async def test_list_users(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        created_user: dict
    ):
        """Test listing all users."""
        response = await client.get("/api/v1/users/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["id"] == created_user["id"] for user in data)


@pytest.mark.users
@pytest.mark.asyncio
class TestUserUpdate:
    """Test updating user information."""
    
    async def test_update_own_user(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        created_user: dict
    ):
        """Test user can update their own information."""
        user_id = created_user["id"]
        update_data = {
            "full_name": "Updated Name",
            "email": "updated@example.com"
        }
        
        response = await client.put(
            f"/api/v1/users/{user_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["email"] == update_data["email"]
    
    async def test_update_password(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        created_user: dict,
        test_user_data: dict
    ):
        """Test updating user password."""
        user_id = created_user["id"]
        new_password = "NewPassword123!"
        
        response = await client.put(
            f"/api/v1/users/{user_id}",
            json={"password": new_password},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify new password works
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["username"],
                "password": new_password
            }
        )
        assert login_response.status_code == 200
    
    async def test_update_other_user_forbidden(
        self, 
        client: AsyncClient, 
        auth_headers: dict
    ):
        """Test that users cannot update other users (non-superuser)."""
        # Try to update a different user (ID 999)
        response = await client.put(
            "/api/v1/users/999",
            json={"full_name": "Hacked Name"},
            headers=auth_headers
        )
        
        # Should be forbidden or not found
        assert response.status_code in [403, 404]
    
    async def test_update_duplicate_email(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        created_user: dict
    ):
        """Test updating to duplicate email fails."""
        # First create another user
        other_user_data = {
            "email": "other@example.com",
            "username": "otheruser",
            "password": "OtherPass123!",
            "full_name": "Other User"
        }
        await client.post("/api/v1/auth/register", json=other_user_data)
        
        # Try to update current user to use other user's email
        user_id = created_user["id"]
        response = await client.put(
            f"/api/v1/users/{user_id}",
            json={"email": other_user_data["email"]},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "email already registered" in response.json()["detail"].lower()
    
    async def test_update_unauthorized(self, client: AsyncClient, created_user: dict):
        """Test updating user without authentication fails."""
        user_id = created_user["id"]
        response = await client.put(
            f"/api/v1/users/{user_id}",
            json={"full_name": "Unauthorized Update"}
        )
        
        assert response.status_code == 401


@pytest.mark.users
@pytest.mark.asyncio
class TestUserPagination:
    """Test user list pagination."""
    
    async def test_list_users_with_pagination(
        self, 
        client: AsyncClient, 
        auth_headers: dict
    ):
        """Test listing users with skip and limit parameters."""
        # Create multiple users
        for i in range(5):
            user_data = {
                "email": f"user{i}@example.com",
                "username": f"user{i}",
                "password": "Password123!",
                "full_name": f"User {i}"
            }
            await client.post("/api/v1/auth/register", json=user_data)
        
        # Test pagination
        response = await client.get(
            "/api/v1/users/?skip=0&limit=3",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3
    
    async def test_list_users_skip(
        self, 
        client: AsyncClient, 
        auth_headers: dict
    ):
        """Test skipping users in list."""
        response = await client.get(
            "/api/v1/users/?skip=1&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
