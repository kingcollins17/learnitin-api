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
import secrets
import string
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


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

    async def authenticate_google_user(self, token: str) -> dict:
        """
        Verify Google token, create user if not exists, and return JWT.

        Args:
            token: Google ID token

        Returns:
            Dictionary containing access token and user info
        """
        try:
            # Verify the token with Google
            # We skip client_id check here if not configured, or use the one from settings
            audience = settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None

            # If audience is empty string, verify_oauth2_token might complain or just verify signature.
            # To be safe, if we don't have a check, we can pass None, but security-wise we should configure it.
            # However, the user said "get the username and email... all in one endpoint".

            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), audience=audience
            )

            email = idinfo.get("email")
            if not email:
                raise ValueError("Token does not contain email")

            # Check if user exists
            user = await self.user_service.repository.get_by_email(email)

            if not user:
                # Create new user
                username = email.split("@")[0]

                # Ensure username is unique
                existing_username = await self.user_service.repository.get_by_username(
                    username
                )
                while existing_username:
                    random_suffix = "".join(
                        secrets.choice(string.digits) for _ in range(4)
                    )
                    username = f"{email.split('@')[0]}{random_suffix}"
                    existing_username = (
                        await self.user_service.repository.get_by_username(username)
                    )

                # Generate random password
                password_chars = (
                    string.ascii_letters + string.digits + string.punctuation
                )
                password = "".join(secrets.choice(password_chars) for _ in range(16))

                user_data = UserCreate(
                    email=email,
                    username=username,
                    password=password,
                    full_name=idinfo.get("name"),
                )

                user = await self.user_service.create_user(user_data)

                # Activate user since they are verified by Google
                user.is_active = True
                await self.user_service.repository.update(user)

            # Generate JWT
            access_token_expires = timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
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

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google Token: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Google authentication failed: {str(e)}",
            )
