"""Tests for authentication feature."""
import pytest
from httpx import AsyncClient


@pytest.mark.auth
@pytest.mark.asyncio
class TestAuthRegistration:
    """Test user registration."""
    
    async def test_register_new_user(self, client: AsyncClient, test_user_data: dict):
        """Test successful user registration."""
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["full_name"] == test_user_data["full_name"]
        assert "id" in data
        assert "hashed_password" not in data  # Password should not be returned
    
    async def test_register_duplicate_email(self, client: AsyncClient, test_user_data: dict, created_user: dict):
        """Test registration with duplicate email fails."""
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        assert "email already registered" in response.json()["detail"].lower()
    
    async def test_register_duplicate_username(self, client: AsyncClient, test_user_data: dict, created_user: dict):
        """Test registration with duplicate username fails."""
        # Try to register with same username but different email
        duplicate_data = test_user_data.copy()
        duplicate_data["email"] = "different@example.com"
        
        response = await client.post("/api/v1/auth/register", json=duplicate_data)
        
        assert response.status_code == 400
        assert "username already taken" in response.json()["detail"].lower()
    
    async def test_register_invalid_email(self, client: AsyncClient, test_user_data: dict):
        """Test registration with invalid email fails."""
        invalid_data = test_user_data.copy()
        invalid_data["email"] = "not-an-email"
        
        response = await client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code == 422  # Validation error


@pytest.mark.auth
@pytest.mark.asyncio
class TestAuthLogin:
    """Test user login."""
    
    async def test_login_success(self, client: AsyncClient, test_user_data: dict, created_user: dict):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["username"],
                "password": test_user_data["password"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
    
    async def test_login_wrong_password(self, client: AsyncClient, test_user_data: dict, created_user: dict):
        """Test login with wrong password fails."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["username"],
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect username or password" in response.json()["detail"].lower()
    
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user fails."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "SomePassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect username or password" in response.json()["detail"].lower()
    
    async def test_login_missing_credentials(self, client: AsyncClient):
        """Test login without credentials fails."""
        response = await client.post("/api/v1/auth/login", data={})
        
        assert response.status_code == 422  # Validation error


@pytest.mark.auth
@pytest.mark.asyncio
class TestAuthToken:
    """Test JWT token functionality."""
    
    async def test_token_can_access_protected_route(
        self, 
        client: AsyncClient, 
        auth_headers: dict
    ):
        """Test that token allows access to protected routes."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "username" in data
    
    async def test_invalid_token_rejected(self, client: AsyncClient):
        """Test that invalid token is rejected."""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    async def test_missing_token_rejected(self, client: AsyncClient):
        """Test that missing token is rejected."""
        response = await client.get("/api/v1/users/me")
        
        assert response.status_code == 401
