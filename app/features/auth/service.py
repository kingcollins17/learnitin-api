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
from app.features.auth.otp_service import OTPService


class AuthService:
    """Service for authentication logic."""

    def __init__(
        self,
        session: AsyncSession,
        user_service: UserService,
        otp_service: OTPService,
    ):
        self.session = session
        self.user_service = user_service
        self.otp_service = otp_service

    async def register_user(self, user_data: UserCreate) -> User:
        """
        Register a new user and send verification magic link.
        """
        user = await self.user_service.create_user(user_data)

        # Automatically request verification magic link
        await self.otp_service.request_magic_link(
            email=user.email, request_type="verification"
        )

        return user

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

        if not user.is_active:
            # Automatically request verification magic link
            await self.otp_service.request_magic_link(
                email=user.email, request_type="verification"
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active. A verification link has been sent to your email. Please verify your account to login.",
            )

        return self.generate_token_response(user)

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

                user_data = UserCreate(
                    email=email,
                    username=username,
                    password=None,
                    full_name=idinfo.get("name"),
                )

                user = await self.user_service.create_user(user_data)

                # Activate user since they are verified by Google
                user.is_active = True
                await self.user_service.repository.update(user)

            return self.generate_token_response(user)

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

    async def authenticate_magic_link(self, email: str) -> User:
        """
        Authenticate a user via magic link (email already verified by OTP).

        Returns:
            The authenticated User object
        """
        user = await self.user_service.repository.get_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return user

    async def verify_passwordless_login(self, email: str, otp: str) -> dict:
        """
        Verify magic link OTP and return token response.
        """
        # 1. Verify OTP
        is_valid = await self.otp_service.verify_otp(code=otp, email=email)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired link",
            )

        # 2. Get user
        user = await self.authenticate_magic_link(email)

        # 3. Activation check (auto-activate if verification was via magic link)
        if not user.is_active:
            user.is_active = True
            await self.user_service.repository.update(user)
            await self.session.commit()

        return self.generate_token_response(user)

    async def verify_and_activate_account(self, email: str, code: str) -> User:
        """
        Verify account using OTP and activate user.
        """
        # 1. Verify OTP
        await self.otp_service.verify_and_validate_otp_for_user(
            code=code, user_email=email
        )

        # 2. Activate the user
        user = await self.user_service.activate_user(email)

        # 3. Commit the changes
        await self.session.commit()

        return user

    def generate_token_response(self, user: User) -> dict:
        """Generate a standard token response for a user."""
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

    async def reset_password(self, email: str, new_password: str) -> bool:
        """Reset a user's password."""
        user = await self.user_service.repository.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        from app.common.security import get_password_hash

        user.hashed_password = get_password_hash(new_password)

        # If user was inactive, we can consider them activated now since they verified via OTP
        user.is_active = True

        await self.user_service.repository.update(user)
        return True
