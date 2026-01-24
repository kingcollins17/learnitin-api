"""User API endpoints."""

from typing import List
import traceback
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session
from app.common.deps import get_current_active_user, get_current_user
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User as UserModel
from app.features.users.schemas import (
    User,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserVerifyRequest,
    DeviceTokenUpdate,
)
from app.features.users.service import UserService
from app.features.auth.otp_service import OTPService
from app.features.auth.otp_repository import OTPRepository
from app.features.subscriptions.dependencies import (
    get_user_subscription,
    get_subscription_usage_service,
)
from app.features.subscriptions.models import Subscription
from app.features.subscriptions.schemas import SubscriptionResponse
from app.features.subscriptions.usage_service import SubscriptionUsageService


router = APIRouter()


@router.get("/me", response_model=ApiResponse[UserResponse])
async def read_users_me(
    current_user: UserModel = Depends(get_current_active_user),
    subscription: Subscription = Depends(get_user_subscription),
    usage_service: SubscriptionUsageService = Depends(get_subscription_usage_service),
):
    """Get current user information."""
    try:
        # Attach subscription to user object for UserResponse schema
        user_response = UserResponse.model_validate(current_user)

        # Attach usage to subscription response
        assert subscription.id is not None
        usage = await usage_service.get_usage(subscription.id)
        subscription_resp = SubscriptionResponse.model_validate(subscription)
        subscription_resp.usage = usage

        user_response.subscription = subscription_resp

        return success_response(
            data=user_response, details="Current user retrieved successfully"
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


@router.post("/verify", response_model=ApiResponse[UserResponse])
async def verify_user(
    data: UserVerifyRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Verify the current user's account using an OTP code.

    **Authentication required** - Users can only verify their own account.
    The user must be signed in (but can be inactive) to use this endpoint.

    This endpoint:
    1. Validates the OTP code exists in the database
    2. Ensures the OTP is associated with the current user's email
    3. Activates the user's account (sets is_active=True)
    4. Marks the OTP as used

    **Request Body:**
    - `code`: The OTP code received via email

    **Response:**
    Returns the updated user with `is_active=True`

    **Error Responses:**
    - `400 Bad Request`: Invalid OTP code or OTP doesn't match user's email
    - `400 Bad Request`: User is already active
    - `401 Unauthorized`: Not authenticated
    - `403 Forbidden`: OTP doesn't belong to the user
    - `500 Internal Server Error`: Server error
    """
    try:
        # Initialize services
        otp_repository = OTPRepository(session)
        otp_service = OTPService(otp_repository)
        user_service = UserService(session)

        # Verify OTP belongs to the current user and mark as used
        await otp_service.verify_and_validate_otp_for_user(
            code=data.code, user_email=current_user.email
        )

        # Activate the user
        user = await user_service.activate_user(current_user.email)

        # Commit the transaction
        await session.commit()

        return success_response(
            data=user, details="User verified and activated successfully"
        )
    except ValueError as e:
        # Handle OTP validation errors from OTPService
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
                if "Invalid OTP" in str(e) or "not associated" in str(e)
                else status.HTTP_403_FORBIDDEN
            ),
            detail=str(e),
        )
    except HTTPException:
        traceback.print_exc()
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify user: {str(e)}",
        )


@router.put("/me/device-token", response_model=ApiResponse[UserResponse])
async def update_device_token(
    data: DeviceTokenUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Update the current user's device registration token for push notifications (FCM).
    """
    try:
        assert current_user.id
        service = UserService(session)
        user = await service.update_device_token(current_user.id, data.device_reg_token)
        await session.commit()
        return success_response(data=user, details="Device token updated successfully")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update device token: {str(e)}",
        )
