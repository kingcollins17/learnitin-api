"""User API endpoints."""

from typing import List
import traceback
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session
from app.common.deps import get_current_active_user
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User as UserModel
from app.features.users.schemas import User, UserCreate, UserUpdate, UserResponse
from app.features.users.service import UserService

router = APIRouter()


@router.get("/me", response_model=ApiResponse[UserResponse])
async def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
    """Get current user information."""
    try:
        return success_response(
            data=current_user, details="Current user retrieved successfully"
        )
    except HTTPException as e:
        traceback.print_exc()
        print(e)
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve current user: {str(e)}",
        )


@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def read_user(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get user by ID (requires authentication)."""
    try:
        service = UserService(session)
        user = await service.get_user(user_id)
        return success_response(data=user, details="User retrieved successfully")
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user: {str(e)}",
        )


@router.put("/{user_id}", response_model=ApiResponse[UserResponse])
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Update user information."""
    try:
        # Users can only update their own information unless they're superuser
        if user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this user",
            )

        service = UserService(session)
        user = await service.update_user(user_id, user_data)
        return success_response(data=user, details="User updated successfully")
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}",
        )


@router.get("/", response_model=ApiResponse[List[UserResponse]])
async def list_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    List all users with pagination.

    **Query Parameters:**
    - `page`: Page number (default: 1)
    - `per_page`: Items per page (default: 10, max: 100)

    **Authentication required.**
    """
    try:
        # Calculate skip and limit from page and per_page
        skip = (page - 1) * per_page
        limit = per_page

        service = UserService(session)
        users = await service.get_users(skip=skip, limit=limit)
        return success_response(
            data=users, details=f"Retrieved {len(users)} users (page {page})"
        )
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}",
        )
