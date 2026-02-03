"""User business logic and service layer."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.models import User
from app.features.users.schemas import UserCreate, UserUpdate
from app.features.users.repository import UserRepository
from app.common.security import get_password_hash, verify_password


class UserService:
    """Service for user business logic."""

    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with hashed password."""
        # Check if user already exists
        existing_user = await self.repository.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        existing_username = await self.repository.get_by_username(user_data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )

        # Create user with hashed password if provided
        hashed_password = (
            get_password_hash(user_data.password) if user_data.password else None
        )
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
        )

        return await self.repository.create(user)

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """Update user information."""
        user = await self.get_user(user_id)
        assert user is not None

        # At this point, user is guaranteed to be User (not None) because get_user raises exception if not found
        # Update fields if provided
        if user_data.email is not None:
            # Check if email is already taken by another user
            existing = await self.repository.get_by_email(user_data.email)
            if existing and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )
            user.email = user_data.email

        if user_data.username is not None:
            # Check if username is already taken by another user
            existing = await self.repository.get_by_username(user_data.username)
            if existing and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )
            user.username = user_data.username

        if user_data.full_name is not None:
            user.full_name = user_data.full_name

        if user_data.password is not None:
            user.hashed_password = get_password_hash(user_data.password)

        user.updated_at = datetime.now(timezone.utc)

        return await self.repository.update(user)

    async def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination."""
        return await self.repository.get_all(skip=skip, limit=limit)

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username and password."""
        user = await self.repository.get_by_email(username)
        if not user or not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def activate_user(self, email: str) -> User:
        """Activate a user account by setting is_active to True."""
        user = await self.repository.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User is already active"
            )

        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)

        return await self.repository.update(user)

    async def update_device_token(self, user_id: int, device_reg_token: str) -> User:
        """Update user's device registration token."""
        user = await self.get_user(user_id)
        assert user is not None
        user.device_reg_token = device_reg_token
        user.updated_at = datetime.now(timezone.utc)
        return await self.repository.update(user)
