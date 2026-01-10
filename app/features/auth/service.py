"""Authentication business logic."""

from datetime import timedelta
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.config import settings
from app.common.security import create_access_token
from app.features.users.models import User
from app.features.users.schemas import UserCreate
from app.features.users.service import UserService


class AuthService:
    """Service for authentication logic."""

    def __init__(self, session: AsyncSession):
        self.user_service = UserService(session)

    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user."""
        return await self.user_service.create_user(user_data)

    async def authenticate_and_get_token(self, username: str, password: str) -> dict:
        """
        Authenticate user and return access token.

        Users can sign in regardless of their is_active status. The client should
        check the is_active field in the response to determine if the user needs
        to verify their account.

        Args:
            username: User's email address
            password: User's password

        Returns:
            Dictionary containing:
            - access_token: JWT token for authentication
            - token_type: Always "bearer"
            - user_id: User's ID
            - email: User's email
            - is_active: Whether the user's account is verified/active

        Raises:
            HTTPException: If credentials are invalid
        """
        user = await self.user_service.authenticate_user(username, password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Allow login even if user is not active
        # Client should check is_active and prompt for verification if needed

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
        }
