"""Common dependencies for FastAPI endpoints."""

import traceback
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.common.security import decode_access_token
from app.common.database.session import get_async_session
from app.features.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Get the current authenticated user."""
    try:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        print(f"token is {token}")
        payload = decode_access_token(token)
        print(f"payload is {payload}")
        if payload is None:
            raise credentials_exception

        user_id: Optional[str] = payload.get("sub")
        print(f"user_id is {user_id}")
        if user_id is None:
            raise credentials_exception

        # Use SQLModel async query
        result = await session.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if user is None:
            raise credentials_exception

        return user
    except Exception as e:
        traceback.print_exc()
        raise e


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user.

    This dependency requires that the user's account is verified (is_active=True).
    Use this for endpoints that should only be accessible to verified users.

    For endpoints that should be accessible to all authenticated users (including
    unverified ones), use `get_current_user` instead.

    Raises:
        HTTPException: 400 if the user's account is not active
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
