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
        """Authenticate user and return access token."""
        user = await self.user_service.authenticate_user(username, password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
