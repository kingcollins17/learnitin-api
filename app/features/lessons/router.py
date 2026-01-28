"""Lesson API endpoints."""

from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException,
    Query,
    Body,
    BackgroundTasks,
)
from typing import List, Optional
from app.features.subscriptions.service import SubscriptionService
import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.database.session import get_async_session, AsyncSessionLocal
from app.common.deps import get_current_active_user
from app.common.responses import ApiResponse, success_response
from app.features.users.models import User
from app.features.subscriptions.dependencies import (
    ResourceAccessControl,
    get_user_subscription,
    get_subscription_service,
    get_subscription_usage_service,
)
from app.features.subscriptions.service import SubscriptionService
from app.features.subscriptions.usage_service import SubscriptionUsageService
from app.features.subscriptions.models import Subscription, SubscriptionResourceType
from app.features.lessons.schemas import (
    LessonResponse,
    LessonDetailResponse,
    LessonCreate,
    LessonUpdate,
    PaginatedLessonsResponse,
    UserLessonResponse,
    UserLessonCreate,
    UserLessonUpdate,
    PaginatedUserLessonsResponse,
    LessonAudioResponse,
    StartLessonResponse,
)
from app.features.lessons.service import LessonService, UserLessonService
from app.features.lessons.lecture_service import lecture_conversion_service
from app.services.audio_generation_service import audio_generation_service
from app.services.storage_service import firebase_storage_service
from app.features.courses.repository import CourseRepository
from app.features.modules.repository import ModuleRepository
from app.features.lessons.generation_service import lesson_generation_service
from app.features.lessons.tasks import (
    generate_audio_background,
    generate_lesson_content_background,
)
from app.features.lessons.lesson_audio_tracker import audio_tracker
from app.features.lessons.lesson_content_tracker import content_tracker

router = APIRouter()


# Lesson Endpoints


@router.get("", response_model=ApiResponse[PaginatedLessonsResponse])
async def get_lessons(
    module_id: int | None = Query(None, description="Filter by module ID"),
    course_id: int | None = Query(None, description="Filter by course ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(100, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get lessons filtered by module or course.

    **Query Parameters:**
    - `module_id`: Filter by module ID (optional)
    - `course_id`: Filter by course ID (optional)
    - `page`: Page number (default: 1)
    - `per_page`: Items per page (default: 100, max: 100)

    **Note:** Provide either module_id or course_id.

    **No authentication required** for public courses.
    """
    try:
        service = LessonService(session)

        if module_id:
            lessons = await service.get_lessons_by_module(
                module_id=module_id, page=page, per_page=per_page
            )
        elif course_id:
            lessons = await service.get_lessons_by_course(
                course_id=course_id, page=page, per_page=per_page
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide either module_id or course_id",
            )

        lessons_response = [LessonResponse.model_validate(l) for l in lessons]

        response_data = PaginatedLessonsResponse(
            lessons=lessons_response,
            page=page,
            per_page=per_page,
            total=len(lessons),
        )

        return success_response(
            data=response_data,
            details=f"Retrieved {len(lessons)} lesson(s)",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch lessons: {str(e)}",
        )


@router.get("/{lesson_id}", response_model=ApiResponse[LessonDetailResponse])
async def get_lesson(
    lesson_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific lesson by ID.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = LessonService(session)
        lesson = await service.get_lesson_by_id(lesson_id)

        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        # Check if lesson is unlocked for the user
        user_lesson_service = UserLessonService(session)
        user_lesson = await user_lesson_service.get_by_user_and_lesson(
            user_id=current_user.id, lesson_id=lesson_id
        )

        if not user_lesson or not user_lesson.is_lesson_unlocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This lesson is locked. You need to start the lesson first.",
            )

        message = "Lesson retrieved successfully"

        # Trigger background generation if content is missing
        if not lesson.content:
            if content_tracker.start_tracking(lesson_id, current_user.id):
                background_tasks.add_task(
                    generate_lesson_content_background,
                    lesson_id=lesson_id,
                    session=session,
                    user_id=current_user.id,
                    course_id=lesson.course_id,
                    module_id=lesson.module_id,
                )
                message = "Lesson content is being prepared. Please check back shortly."
            else:
                message = (
                    "Lesson content is already being prepared. Please wait a moment."
                )

        return success_response(
            data=lesson,
            details=message,
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch lesson: {str(e)}",
        )


@router.patch("/{lesson_id}", response_model=ApiResponse[LessonDetailResponse])
async def update_lesson(
    lesson_id: int,
    lesson_update: LessonUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a lesson.

    **Authentication required.**
    """
    try:
        service = LessonService(session)
        updated_lesson = await service.update_lesson(
            lesson_id=lesson_id,
            lesson_update=lesson_update.model_dump(exclude_unset=True),
        )

        return success_response(
            data=updated_lesson,
            details="Lesson updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lesson: {str(e)}",
        )


# UserLesson Endpoints


@router.post("/{lesson_id}/start", response_model=ApiResponse[StartLessonResponse])
async def start_lesson(
    lesson_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
    _access: None = Depends(ResourceAccessControl(SubscriptionResourceType.LESSON)),
    subscription: Subscription = Depends(get_user_subscription),
    usage_service: SubscriptionUsageService = Depends(get_subscription_usage_service),
):
    """
    Start a lesson (create user lesson progress record).

    **Authentication required.**
    """
    try:
        assert current_user.id

        # 1. Fetch lesson details first to get context (module_id, course_id)
        lesson_service = LessonService(session)
        lesson = await lesson_service.get_lesson_by_id(lesson_id)

        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        # Check if user is enrolled in the course
        user_lesson_service = UserLessonService(session)
        is_enrolled = await user_lesson_service.is_user_enrolled(
            user_id=current_user.id, course_id=lesson.course_id
        )

        if not is_enrolled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be enrolled in the course to start a lesson",
            )

        # 2. Start the lesson (create record)
        user_lesson = await user_lesson_service.start_lesson(
            user_id=current_user.id,
            lesson_id=lesson_id,
            module_id=lesson.module_id,
            course_id=lesson.course_id,
            usage_service=usage_service,
            subscription=subscription,
        )
        await session.commit()

        # 3. Check and handle content availability
        is_content_available = True
        message = "Lesson started successfully"

        if not lesson.content:
            is_content_available = False
            # Trigger background generation if not already in progress
            if content_tracker.start_tracking(lesson_id, current_user.id):
                background_tasks.add_task(
                    generate_lesson_content_background,
                    lesson_id=lesson_id,
                    session=session,
                    user_id=current_user.id,
                    course_id=lesson.course_id,
                    module_id=lesson.module_id,
                )
                message = "Lesson content is being prepared. You will be notified when it's ready."
            else:
                message = (
                    "Lesson content is already being prepared. Please wait a moment."
                )

        response_data = StartLessonResponse(
            user_lesson=UserLessonResponse.model_validate(user_lesson),
            is_content_available=is_content_available,
        )

        return success_response(
            data=response_data,
            details=message,
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start lesson: {str(e)}",
        )


@router.get("/user/lessons", response_model=ApiResponse[PaginatedUserLessonsResponse])
async def get_user_lessons(
    module_id: int | None = Query(None, description="Filter by module ID"),
    course_id: int | None = Query(None, description="Filter by course ID"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all user lessons filtered by module or course.

    **Query Parameters:**
    - `module_id`: Filter by module ID (optional)
    - `course_id`: Filter by course ID (optional)

    **Note:** Provide either module_id or course_id.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = UserLessonService(session)

        if module_id:
            user_lessons = await service.get_user_lessons_by_module(
                user_id=current_user.id,
                module_id=module_id,
            )
        elif course_id:
            user_lessons = await service.get_user_lessons_by_course(
                user_id=current_user.id,
                course_id=course_id,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide either module_id or course_id",
            )

        user_lessons_response = [
            UserLessonResponse.model_validate(ul) for ul in user_lessons
        ]

        response_data = PaginatedUserLessonsResponse(
            user_lessons=user_lessons_response,
            page=1,
            per_page=len(user_lessons),
            total=len(user_lessons),
        )

        return success_response(
            data=response_data,
            details=f"Retrieved {len(user_lessons)} user lesson(s)",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user lessons: {str(e)}",
        )


@router.get("/user/lessons/detail", response_model=ApiResponse[UserLessonResponse])
async def get_user_lesson(
    lesson_id: int = Query(..., description="ID of the lesson"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get user lesson progress for a specific lesson.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = UserLessonService(session)
        user_lesson = await service.get_user_lesson(
            user_id=current_user.id,
            lesson_id=lesson_id,
        )

        return success_response(
            data=user_lesson,
            details="User lesson retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user lesson: {str(e)}",
        )


@router.patch("/user/lessons/update", response_model=ApiResponse[UserLessonResponse])
async def update_user_lesson(
    lesson_id: int = Query(..., description="ID of the lesson"),
    user_lesson_update: Optional[UserLessonUpdate] = Body(None),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update user lesson progress.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = UserLessonService(session)

        update_data = (
            user_lesson_update.model_dump(exclude_unset=True)
            if user_lesson_update
            else {}
        )

        user_lesson = await service.update_user_lesson(
            user_id=current_user.id,
            lesson_id=lesson_id,
            update_data=update_data,
        )

        return success_response(
            data=user_lesson,
            details="User lesson updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user lesson: {str(e)}",
        )


@router.post("/user/lessons/unlock", response_model=ApiResponse[UserLessonResponse])
async def unlock_lesson(
    lesson_id: int = Query(..., description="ID of the lesson"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Unlock a lesson for the current user.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = UserLessonService(session)
        user_lesson = await service.unlock_lesson(
            user_id=current_user.id,
            lesson_id=lesson_id,
        )

        return success_response(
            data=user_lesson,
            details="Lesson unlocked successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unlock lesson: {str(e)}",
        )


@router.post(
    "/user/lessons/unlock-audio", response_model=ApiResponse[UserLessonResponse]
)
async def unlock_audio(
    background_tasks: BackgroundTasks,
    lesson_id: int = Query(..., description="ID of the lesson"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
    _access: None = Depends(ResourceAccessControl(SubscriptionResourceType.AUDIO)),
    subscription: Subscription = Depends(get_user_subscription),
    usage_service: SubscriptionUsageService = Depends(get_subscription_usage_service),
):
    """
    Unlock audio for a lesson.

    Generates audio if missing and marks as unlocked.
    """
    try:
        assert current_user.id
        lesson_service = LessonService(session)
        service = UserLessonService(session)

        # 1. Get the lesson
        lesson = await lesson_service.get_lesson_by_id(lesson_id)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        # 2. Unlock audio for user (usage increment is now inside this service call)
        user_lesson = await service.unlock_audio(
            user_id=current_user.id,
            lesson_id=lesson_id,
            usage_service=usage_service,
            subscription=subscription,
        )
        await session.commit()

        # 3. Check for existing audio parts
        existing_audios = await lesson_service.get_audios_by_lesson_id(lesson_id)
        message = "Audio unlocked successfully"

        if not existing_audios:
            if not lesson.content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Lesson content is empty, cannot generate audio.",
                )

            # Trigger background generation if not already in progress
            if audio_tracker.start_tracking(lesson_id, current_user.id):
                background_tasks.add_task(
                    generate_audio_background,
                    lesson_id=lesson_id,
                    session=session,
                    user_id=current_user.id,
                )
                message = "Audio is being prepared. Please check back shortly."
            else:
                message = "Audio is already being prepared. Please check back shortly."

        # Prepare response with audio parts
        response = UserLessonResponse.model_validate(user_lesson)
        # Include audio parts in response
        response.audios = [
            LessonAudioResponse.model_validate(audio) for audio in existing_audios
        ]

        return success_response(
            data=response,
            details=message,
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unlock audio: {str(e)}",
        )


@router.post(
    "/user/lessons/complete-quiz", response_model=ApiResponse[UserLessonResponse]
)
async def complete_quiz(
    lesson_id: int = Query(..., description="ID of the lesson"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Mark quiz as completed for a lesson.

    **Authentication required.**
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
            details="Quiz completed successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete quiz: {str(e)}",
        )


@router.post("/user/lessons/complete", response_model=ApiResponse[UserLessonResponse])
async def complete_lesson(
    lesson_id: int = Query(..., description="ID of the lesson"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Mark a lesson as completed.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = UserLessonService(session)
        user_lesson = await service.complete_lesson(
            user_id=current_user.id,
            lesson_id=lesson_id,
        )

        return success_response(
            data=user_lesson,
            details="Lesson completed successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete lesson: {str(e)}",
        )


@router.post(
    "/{lesson_id}/generate-audio", response_model=ApiResponse[LessonDetailResponse]
)
async def generate_audio(
    lesson_id: int,
    bg: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate and save audio transcript for a lesson.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = LessonService(session)
        lesson = await service.get_lesson_by_id(lesson_id)

        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        if audio_tracker.start_tracking(lesson_id, current_user.id):
            bg.add_task(
                generate_audio_background,
                lesson_id=lesson_id,
                session=session,
                user_id=current_user.id,
            )

            return success_response(
                data=lesson,
                details="Audio generation started in background",
            )
        else:
            return success_response(
                data=lesson,
                details="Audio generation is already in progress",
            )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate audio: {str(e)}",
        )


@router.get(
    "/{lesson_id}/audios", response_model=ApiResponse[List[LessonAudioResponse]]
)
async def get_lesson_audios(
    lesson_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all audio segments for a lesson.

    **Access Restricted:**
    - Must have started the lesson (UserLesson record exists).
    - Audio must be unlocked for the user.

    **Authentication required.**
    """
    try:
        assert current_user.id
        service = LessonService(session)
        audios = await service.get_lesson_audios(
            user_id=current_user.id, lesson_id=lesson_id
        )

        return success_response(
            data=audios,
            details=f"Retrieved {len(audios)} audio segment(s)",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch lesson audios: {str(e)}",
        )
