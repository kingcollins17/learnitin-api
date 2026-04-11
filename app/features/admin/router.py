"""Admin API endpoints."""

import traceback
from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_active_user
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User as UserModel
from app.features.users.schemas import UserResponse
from app.features.admin.schemas import (
    AdminUserListResponse,
    AdminBanUserRequest,
    AdminGrantPremiumRequest,
    AdminBroadcastNotificationRequest,
    AdminNotifyUserRequest,
    AdminNotifyUsersRequest,
    AdminStatsResponse,
)
from app.features.admin.service import AdminService
from app.features.subscriptions.schemas import SubscriptionResponse

router = APIRouter()


# ========== Admin Auth Dependency ==========


async def get_current_admin_user(
    current_user: UserModel = Depends(get_current_active_user),
) -> UserModel:
    """Require the current user to be a superuser (admin).

    Raises:
        HTTPException: 403 if user is not an admin.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# Import the dependency factory (defined in common/dependencies.py)
from app.common.dependencies import get_admin_service


# ========== User Management ==========


from datetime import datetime


@router.get("/users", response_model=ApiResponse[AdminUserListResponse])
async def admin_list_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email, username, or full name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_superuser: Optional[bool] = Query(None, description="Filter by admin status"),
    created_after: Optional[datetime] = Query(None, description="Filter users created after this date (ISO 8601)"),
    created_before: Optional[datetime] = Query(None, description="Filter users created before this date (ISO 8601)"),
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """List all users with pagination and multi-dimensional filtering.

    **Admin only.** Supports text search and filters for is_active, is_superuser, and date range.
    """
    try:
        result = await service.list_users(
            page=page,
            per_page=per_page,
            search=search,
            is_active=is_active,
            is_superuser=is_superuser,
            created_after=created_after,
            created_before=created_before,
        )
        return success_response(data=result, details=f"Retrieved {len(result.items)} users (page {page})")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}",
        )


@router.get("/users/{user_id}", response_model=ApiResponse[UserResponse])
async def admin_get_user(
    user_id: int,
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Get detailed user information by ID.

    **Admin only.**
    """
    try:
        user = await service.get_user(user_id)
        return success_response(data=user, details="User retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}",
        )


@router.post("/users/{user_id}/ban", response_model=ApiResponse[UserResponse])
async def admin_ban_user(
    user_id: int,
    body: AdminBanUserRequest = AdminBanUserRequest(),
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Ban a user by deactivating their account.

    **Admin only.** Sets user's `is_active` to False.
    """
    try:
        user = await service.ban_user(user_id, reason=body.reason)
        await service.commit_all()
        return success_response(data=user, details=f"User {user_id} has been banned")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ban user: {str(e)}",
        )


@router.post("/users/{user_id}/unban", response_model=ApiResponse[UserResponse])
async def admin_unban_user(
    user_id: int,
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Unban a user by reactivating their account.

    **Admin only.** Sets user's `is_active` to True.
    """
    try:
        user = await service.unban_user(user_id)
        await service.commit_all()
        return success_response(data=user, details=f"User {user_id} has been unbanned")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unban user: {str(e)}",
        )


# ========== Subscription Management ==========


@router.post(
    "/users/{user_id}/grant-premium",
    response_model=ApiResponse[SubscriptionResponse],
)
async def admin_grant_premium(
    user_id: int,
    body: AdminGrantPremiumRequest,
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Grant premium subscription to a user without Google Play.

    **Admin only.** Creates a new active subscription with the given duration.
    """
    try:
        sub = await service.grant_premium(
            user_id,
            duration_days=body.duration_days,
            product_id=body.product_id,
        )
        await service.commit_all()
        return success_response(
            data=sub,
            details=f"Premium granted to user {user_id} for {body.duration_days} days",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant premium: {str(e)}",
        )


@router.post(
    "/users/{user_id}/revoke-premium",
    response_model=ApiResponse[SubscriptionResponse],
)
async def admin_revoke_premium(
    user_id: int,
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Revoke premium subscription and revert to free plan.

    **Admin only.**
    """
    try:
        sub = await service.revoke_premium(user_id)
        await service.commit_all()
        return success_response(
            data=sub,
            details=f"Premium revoked for user {user_id}, reverted to free plan",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke premium: {str(e)}",
        )


# ========== Platform Stats ==========


@router.get("/stats", response_model=ApiResponse[AdminStatsResponse])
async def admin_get_stats(
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Get platform-wide statistics.

    **Admin only.** Returns aggregate counts of users, courses, lessons, and subscriptions.
    """
    try:
        stats = await service.get_platform_stats()
        return success_response(data=stats, details="Platform stats retrieved")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}",
        )


# ========== Course Management ==========


@router.get("/courses", response_model=ApiResponse)
async def admin_list_courses(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    creator_id: Optional[int] = Query(None, description="Filter by creator user ID"),
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """List all courses with pagination and optional creator filter.

    **Admin only.**
    """
    try:
        result = await service.list_courses(
            page=page, per_page=per_page, creator_id=creator_id
        )
        return success_response(
            data=result,
            details=f"Retrieved {len(result['items'])} courses (page {page})",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list courses: {str(e)}",
        )


@router.delete("/courses/{course_id}", response_model=ApiResponse)
async def admin_delete_course(
    course_id: int,
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Delete a course and all its children (modules, lessons, audios).

    **Admin only.** Also removes course image from Firebase Storage.
    """
    try:
        result = await service.delete_course(course_id)
        await service.commit_all()
        return success_response(data=result, details=f"Course {course_id} deleted")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete course: {str(e)}",
        )


# ========== Audio Management ==========


@router.get("/lessons/{lesson_id}/audios", response_model=ApiResponse)
async def admin_list_lesson_audios(
    lesson_id: int,
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """List all audio files for a given lesson.

    **Admin only.**
    """
    try:
        audios = await service.list_lesson_audios(lesson_id)
        return success_response(
            data=audios, details=f"Retrieved {len(audios)} audios for lesson {lesson_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list audios: {str(e)}",
        )


@router.delete("/audios/{audio_id}", response_model=ApiResponse)
async def admin_delete_audio(
    audio_id: int,
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Delete a stale or unwanted audio from Firebase Storage and database.

    **Admin only.** Irreversible operation.
    """
    try:
        result = await service.delete_audio(audio_id)
        await service.commit_all()
        return success_response(data=result, details=f"Audio {audio_id} deleted")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete audio: {str(e)}",
        )


# ========== Notification Management ==========


@router.post("/notifications/broadcast", response_model=ApiResponse)
async def admin_broadcast_notification(
    body: AdminBroadcastNotificationRequest,
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Broadcast a notification to all active users via bubus event bus.

    **Admin only.**
    """
    try:
        result = await service.broadcast_notification(
            title=body.title, message=body.message, type=body.type
        )
        return success_response(data=result, details="Broadcast sent")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to broadcast notification: {str(e)}",
        )


@router.post("/notifications/send", response_model=ApiResponse)
async def admin_notify_user(
    body: AdminNotifyUserRequest,
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Send a notification to a single user via bubus event bus.

    **Admin only.**
    """
    try:
        result = await service.notify_user(
            user_id=body.user_id,
            title=body.title,
            message=body.message,
            type=body.type,
        )
        return success_response(data=result, details="Notification sent")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}",
        )


@router.post("/notifications/send-bulk", response_model=ApiResponse)
async def admin_notify_users(
    body: AdminNotifyUsersRequest,
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Send notifications to a list of users via bubus event bus.

    **Admin only.**
    """
    try:
        result = await service.notify_users(
            user_ids=body.user_ids,
            title=body.title,
            message=body.message,
            type=body.type,
        )
        return success_response(data=result, details="Bulk notification sent")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send bulk notification: {str(e)}",
        )


# ========== Maintenance ==========


@router.post("/maintenance/run", response_model=ApiResponse)
async def admin_run_maintenance(
    service: AdminService = Depends(get_admin_service),
    admin: UserModel = Depends(get_current_admin_user),
):
    """Trigger database maintenance tasks (orphan cleanup, etc.).

    **Admin only.** Runs cleanup for orphaned audios and courses.
    """
    try:
        results = await service.run_maintenance()
        return success_response(data=results, details="Maintenance completed")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run maintenance: {str(e)}",
        )
