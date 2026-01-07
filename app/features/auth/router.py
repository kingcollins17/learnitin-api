"""Authentication API endpoints."""
from fastapi import APIRouter, Depends, status, HTTPException
import traceback
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session
from app.common.responses import ApiResponse, success_response
from app.features.auth.schemas import Token
from app.features.auth.service import AuthService
from app.features.users.schemas import UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Register a new user."""
    try:
        service = AuthService(session)
        user = await service.register_user(user_data)
        return success_response(
            data=user,
            details="User registered successfully",
            status_code=201
        )
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session)
):
    """Login and get access token."""
    try:
        service = AuthService(session)
        token_data = await service.authenticate_and_get_token(
            form_data.username,
            form_data.password
        )
        return token_data
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


