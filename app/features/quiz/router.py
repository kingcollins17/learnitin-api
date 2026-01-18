"""Quiz API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import traceback

from app.common.database.session import get_async_session
from app.common.deps import get_current_active_user
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User
from app.features.quiz.schemas import QuizResponse
from app.features.quiz.service import QuizService
from app.features.lessons.service import LessonService, UserLessonService
from app.features.lessons.schemas import UserLessonResponse

router = APIRouter()


@router.get("/lesson/{lesson_id}", response_model=ApiResponse[QuizResponse])
async def get_quiz(
    lesson_id: int,
    generate_if_missing: bool = Query(
        True, description="Generate quiz if it doesn't exist"
    ),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get quiz for a specific lesson.

    If `generate_if_missing` is True and no quiz exists, it will trigger AI generation.
    """
    try:
        service = QuizService(session)
        lesson_service = LessonService(session)

        # 1. Check if quiz exists
        quiz = await service.get_quiz_by_lesson(lesson_id)

        if not quiz and generate_if_missing:
            # 2. Get lesson details to ensure it exists and has content
            lesson = await lesson_service.get_lesson_by_id(lesson_id)
            if not lesson:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Lesson not found",
                )

            if not lesson.content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Lesson content is empty. Cannot generate quiz.",
                )

            # 3. Generate quiz
            quiz = await service.generate_and_save_quiz(lesson)

        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found for this lesson.",
            )

        return success_response(
            data=quiz,
            details="Quiz retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch quiz: {str(e)}",
        )


@router.post("/lesson/{lesson_id}/generate", response_model=ApiResponse[QuizResponse])
async def generate_quiz(
    lesson_id: int,
    question_count: int = Query(5, ge=1, le=10),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Manually trigger AI generation for a lesson quiz.

    Note: If a quiz already exists, this might fail due to the unique constraint
    unless we implement deletion or update logic.
    """
    try:
        service = QuizService(session)
        lesson_service = LessonService(session)

        # 1. Check if lesson exists
        lesson = await lesson_service.get_lesson_by_id(lesson_id)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        if not lesson.content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lesson content is empty. Cannot generate quiz.",
            )

        # 2. Check if quiz exists - if so, we might want to delete it or return error
        existing = await service.get_quiz_by_lesson(lesson_id)
        if existing:
            # For now, let's just return the existing one or tell them to delete first
            return success_response(
                data=existing,
                details="Quiz already exists. Use GET to retrieve it.",
            )

        # 3. Generate quiz
        quiz = await service.generate_and_save_quiz(
            lesson, question_count=question_count
        )

        return success_response(
            data=quiz,
            details="Quiz generated and saved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quiz: {str(e)}",
        )


@router.post(
    "/lesson/{lesson_id}/complete", response_model=ApiResponse[UserLessonResponse]
)
async def complete_quiz(
    lesson_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Mark quiz as completed for a specific lesson for the current user.
    """
    try:
        assert current_user.id
        service = UserLessonService(session)
        user_lesson = await service.complete_quiz(
            user_id=current_user.id,
            lesson_id=lesson_id,
        )

        return success_response(
            data=user_lesson,
            details="Quiz marked as completed successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete quiz: {str(e)}",
        )
