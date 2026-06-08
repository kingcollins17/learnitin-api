"""Quiz API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import traceback

from app.common.database.session import get_async_session
from app.common.deps import get_current_active_user, HasSufficientLessonCredits
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User
from app.features.quiz.schemas import QuizResponse
from app.features.quiz.service import QuizService
from app.features.lessons.service import LessonService, UserLessonService
from app.features.lessons.schemas import UserLessonResponse
from app.common.dependencies import (
    get_quiz_service,
    get_lesson_service,
    get_user_lesson_service,
)

router = APIRouter()


@router.get("/lesson/{lesson_id}", response_model=ApiResponse[QuizResponse])
async def get_quiz(
    lesson_id: int,
    generate_if_missing: bool = Query(
        True, description="Generate quiz if it doesn't exist"
    ),
    current_user: User = Depends(get_current_active_user),
    service: QuizService = Depends(get_quiz_service),
    lesson_service: LessonService = Depends(get_lesson_service),
    user_lesson_service: UserLessonService = Depends(get_user_lesson_service),
):
    """
    Get quiz for a specific lesson.

    If `generate_if_missing` is True and no quiz exists, it will trigger AI generation.
    """
    try:
        assert current_user.id, 'User ID cannot be None'

        # 1. Check if the quiz is unlocked for the user. If not, unlock it.
        # This must happen before checking if the quiz exists or generating it.
        user_lesson = await user_lesson_service.get_user_lesson(
            user_id=current_user.id,
            lesson_id=lesson_id,
        )
        if not user_lesson:
            raise HTTPException(status_code=404, detail='User lesson not found')
        if not user_lesson.is_quiz_unlocked:
            await user_lesson_service.unlock_quiz(
                user_id=current_user.id,
                lesson_id=lesson_id,
            )
            await user_lesson_service.commit_all()

        # 2. Check if quiz exists
        quiz = await service.get_quiz_by_lesson(lesson_id)

        if not quiz and generate_if_missing:
            # 3. Get lesson details to ensure it exists and has content
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

            # 4. Generate quiz
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
    service: QuizService = Depends(get_quiz_service),
    lesson_service: LessonService = Depends(get_lesson_service),
    user_lesson_service: UserLessonService = Depends(get_user_lesson_service),
    _credits: User = Depends(HasSufficientLessonCredits("quiz")),
):
    """
    Manually trigger AI generation for a lesson quiz.

    Note: If a quiz already exists, this might fail due to the unique constraint
    unless we implement deletion or update logic.
    """
    try:
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

        # Ensure the quiz is unlocked (and credits deducted) via the service if not already unlocked
        assert current_user.id, 'User ID cannot be None'
        user_lesson = await user_lesson_service.get_user_lesson(
            user_id=current_user.id,
            lesson_id=lesson_id,
        )
        assert user_lesson, 'User lesson not found'
        if not user_lesson.is_quiz_unlocked:
            await user_lesson_service.unlock_quiz(
                user_id=current_user.id,
                lesson_id=lesson_id,
            )
            await user_lesson_service.commit_all()

        # 2. Check if quiz exists - if so, return it
        existing = await service.get_quiz_by_lesson(lesson_id)
        if existing:
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
    service: UserLessonService = Depends(get_user_lesson_service),
):
    """
    Mark quiz as completed for a specific lesson for the current user.
    """
    try:
        assert current_user.id
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
