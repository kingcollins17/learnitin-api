"""Router for streaks API endpoints."""

import traceback
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.common.dependencies import get_streak_service
from app.common.deps import get_current_active_user
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User
from .schemas import CourseStreakResponse, DashboardStatsResponse
from .service import StreakService

router = APIRouter()


@router.get("/dashboard", response_model=ApiResponse[DashboardStatsResponse])
async def get_dashboard_stats(
    timezone: str = Query("UTC", description="User local timezone"),
    current_user: User = Depends(get_current_active_user),
    service: StreakService = Depends(get_streak_service),
):
    """
    Get aggregated study and course completion statistics for the user dashboard.
    """
    try:
        assert current_user.id
        stats = await service.get_dashboard_stats(user_id=current_user.id, timezone_str=timezone)
        return success_response(
            data=stats,
            details="Dashboard statistics retrieved successfully",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard stats: {str(e)}",
        )


@router.get("/courses", response_model=ApiResponse[List[CourseStreakResponse]])
async def get_course_streaks(
    timezone: str = Query("UTC", description="User local timezone"),
    current_user: User = Depends(get_current_active_user),
    service: StreakService = Depends(get_streak_service),
):
    """
    Get streak statistics and 7-day week activity for all courses the user is enrolled in.
    """
    try:
        assert current_user.id
        # Get enrolled courses
        user_courses = await service.user_course_repo.get_by_user_with_course(user_id=current_user.id, limit=100)

        results: List[CourseStreakResponse] = []
        for uc in user_courses:
            if not uc.course:
                continue
            streak_info = await service.calculate_streak_stats(
                user_id=current_user.id,
                course_id=uc.course_id,
                course_name=uc.course.title,
                timezone_str=timezone,
            )
            results.append(streak_info)

        return success_response(
            data=results,
            details=f"Retrieved streak details for {len(results)} course(s)",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch course streaks: {str(e)}",
        )


@router.get("/course/{course_id}", response_model=ApiResponse[CourseStreakResponse])
async def get_course_streak_detail(
    course_id: int,
    timezone: str = Query("UTC", description="User local timezone"),
    current_user: User = Depends(get_current_active_user),
    service: StreakService = Depends(get_streak_service),
):
    """
    Get streak statistics and 7-day week activity for a specific course.
    """
    try:
        assert current_user.id
        # Check course enrollment
        user_course = await service.user_course_repo.get_by_user_and_course_with_details(
            user_id=current_user.id, course_id=course_id
        )
        if not user_course or not user_course.course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course enrollment not found",
            )

        streak_info = await service.calculate_streak_stats(
            user_id=current_user.id,
            course_id=course_id,
            course_name=user_course.course.title,
            timezone_str=timezone,
        )

        return success_response(
            data=streak_info,
            details="Course streak details retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch course streak: {str(e)}",
        )
