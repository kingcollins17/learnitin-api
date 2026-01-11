"""Service for managing lessons."""

from fastapi import HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.features.lessons.repository import LessonRepository, UserLessonRepository
from app.features.lessons.models import Lesson, UserLesson
from app.features.courses.models import ProgressStatus
from app.features.lessons.generation_service import lesson_generation_service
from app.features.modules.repository import ModuleRepository, UserModuleRepository
from app.features.modules.service import UserModuleService
from app.features.courses.repository import CourseRepository, UserCourseRepository


class LessonService:
    """Service for lesson business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = LessonRepository(session)
        self.course_repo = CourseRepository(session)
        self.module_repo = ModuleRepository(session)
        self.generation_service = lesson_generation_service

    async def generate_content(self, lesson_id: int) -> Optional[Lesson]:
        """
        Generate content for a lesson and update it.

        Args:
            lesson_id: ID of the lesson to generate content for

        Returns:
            Updated lesson with generated content
        """
        lesson = await self.repository.get_by_id(lesson_id)
        if not lesson:
            return None

        course = await self.course_repo.get_by_id(lesson.course_id)
        module = await self.module_repo.get_by_id(lesson.module_id)

        if not course or not module:
            # Should not happen in consistent DB, but good to handle
            return None

        content = await self.generation_service.generate_lesson_content(
            course=course, module=module, lesson=lesson
        )

        lesson.content = content
        return await self.repository.update(lesson)

    async def generate_audio_transcription(self, lesson_id: int) -> str:
        """
        Generate (mock) audio transcription for a lesson.

        Args:
            lesson_id: ID of the lesson

        Returns:
            URL to the mock audio transcription
        """
        # In a real implementation, this would call a TTS service
        return f"https://storage.example.com/audio/lessons/{lesson_id}.mp3"

    async def update_content_markdown(
        self, lesson_id: int, content_update: str
    ) -> Optional[Lesson]:
        """
        Update the markdown content of a lesson.

        Args:
            lesson_id: ID of the lesson
            content_update: New markdown content

        Returns:
            Updated lesson
        """
        lesson = await self.repository.get_by_id(lesson_id)
        if not lesson:
            return None

        lesson.content = content_update
        return await self.repository.update(lesson)

    async def get_lesson(self, lesson_id: int) -> Optional[Lesson]:
        """Get lesson by ID."""
        return await self.repository.get_by_id(lesson_id)

    async def get_lessons_by_module(
        self, module_id: int, page: int = 1, per_page: int = 100
    ) -> List[Lesson]:
        """
        Get all lessons for a specific module.

        Args:
            module_id: ID of the module
            page: Page number (1-indexed)
            per_page: Number of items per page

        Returns:
            List of lessons for the module
        """
        skip = (page - 1) * per_page
        return await self.repository.get_by_module_id(
            module_id=module_id, skip=skip, limit=per_page
        )

    async def get_lessons_by_course(
        self, course_id: int, page: int = 1, per_page: int = 100
    ) -> List[Lesson]:
        """
        Get all lessons for a specific course.

        Args:
            course_id: ID of the course
            page: Page number (1-indexed)
            per_page: Number of items per page

        Returns:
            List of lessons for the course
        """
        skip = (page - 1) * per_page
        return await self.repository.get_by_course_id(
            course_id=course_id, skip=skip, limit=per_page
        )

    async def get_lesson_by_id(self, lesson_id: int) -> Optional[Lesson]:
        """
        Get lesson by ID.

        Args:
            lesson_id: ID of the lesson

        Returns:
            Lesson if found, None otherwise
        """
        return await self.repository.get_by_id(lesson_id)

    async def create_lesson(self, lesson_data: dict) -> Lesson:
        """
        Create a new lesson.

        Args:
            lesson_data: Dictionary containing lesson data

        Returns:
            Created Lesson object
        """
        lesson = Lesson(**lesson_data)
        return await self.repository.create(lesson)

    async def update_lesson(self, lesson_id: int, lesson_update: dict) -> Lesson:
        """
        Update a lesson.

        Args:
            lesson_id: ID of the lesson to update
            lesson_update: Dictionary of fields to update

        Returns:
            Updated Lesson object

        Raises:
            HTTPException: If lesson not found
        """
        lesson = await self.repository.get_by_id(lesson_id)

        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        # Update only provided fields
        for field, value in lesson_update.items():
            if value is not None and hasattr(lesson, field):
                setattr(lesson, field, value)

        # Update timestamp
        lesson.updated_at = datetime.now(timezone.utc)

        return await self.repository.update(lesson)

    async def delete_lesson(self, lesson_id: int) -> None:
        """
        Delete a lesson.

        Args:
            lesson_id: ID of the lesson to delete

        Raises:
            HTTPException: If lesson not found
        """
        lesson = await self.repository.get_by_id(lesson_id)

        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        await self.repository.delete(lesson)


class UserLessonService:
    """Service for user lesson business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserLessonRepository(session)
        self.lesson_repo = LessonRepository(session)
        self.user_course_repo = UserCourseRepository(session)
        self.user_module_repo = UserModuleRepository(session)
        self.user_module_service = UserModuleService(session)

    async def start_lesson(
        self, user_id: int, lesson_id: int, module_id: int, course_id: int
    ) -> UserLesson:
        """
        Start a lesson for a user (create user lesson record).

        Args:
            user_id: ID of the user
            lesson_id: ID of the lesson
            module_id: ID of the module
            course_id: ID of the course

        Returns:
            Created UserLesson object

        Raises:
            HTTPException: If user lesson already exists
        """
        # Check if already started
        existing = await self.repository.get_by_user_and_lesson(user_id, lesson_id)

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has already started this lesson",
            )

        # Check and start module if needed
        # We try to get the user module directly to see if it exists
        user_module = await self.user_module_repo.get_by_user_and_module(
            user_id=user_id, module_id=module_id
        )
        if not user_module:
            # Start the module automatically
            await self.user_module_service.start_module(
                user_id=user_id, module_id=module_id, course_id=course_id
            )

        # Check if previous lesson is completed
        current_lesson = await self.lesson_repo.get_by_id(lesson_id)
        if not current_lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        previous_lesson = await self.lesson_repo.get_previous_lesson(
            module_id=module_id,
            current_order=current_lesson.order,
        )

        if previous_lesson:
            assert previous_lesson.id is not None
            user_previous_lesson = await self.repository.get_by_user_and_lesson(
                user_id=user_id,
                lesson_id=previous_lesson.id,
            )
            if (
                not user_previous_lesson
                or user_previous_lesson.status != ProgressStatus.COMPLETED
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"You must complete the previous lesson '{previous_lesson.title}' before starting this one.",
                )

        # Create user lesson record
        user_lesson = UserLesson(
            user_id=user_id,
            lesson_id=lesson_id,
            module_id=module_id,
            course_id=course_id,
            status=ProgressStatus.IN_PROGRESS,
        )

        created_user_lesson = await self.repository.create(user_lesson)

        # Update UserCourse progress
        user_course = await self.user_course_repo.get_by_user_and_course(
            user_id, course_id
        )
        if user_course:
            user_course.current_lesson_id = lesson_id
            user_course.current_module_id = module_id
            user_course.updated_at = datetime.now(timezone.utc)
            await self.user_course_repo.update(user_course)

        return created_user_lesson

    async def get_user_lessons_by_module(
        self, user_id: int, module_id: int
    ) -> List[UserLesson]:
        """
        Get all user lessons for a specific module.

        Args:
            user_id: ID of the user
            module_id: ID of the module

        Returns:
            List of user lessons for the module
        """
        return await self.repository.get_by_user_and_module(user_id, module_id)

    async def get_user_lessons_by_course(
        self, user_id: int, course_id: int
    ) -> List[UserLesson]:
        """
        Get all user lessons for a specific course.

        Args:
            user_id: ID of the user
            course_id: ID of the course

        Returns:
            List of user lessons for the course
        """
        return await self.repository.get_by_user_and_course(user_id, course_id)

    async def get_user_lesson(
        self, user_id: int, lesson_id: int
    ) -> Optional[UserLesson]:
        """
        Get user lesson by lesson ID.

        Args:
            user_id: ID of the user
            lesson_id: ID of the lesson

        Returns:
            UserLesson if found

        Raises:
            HTTPException: If user lesson not found
        """
        user_lesson = await self.repository.get_by_user_and_lesson(user_id, lesson_id)

        if not user_lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User lesson not found",
            )

        return user_lesson

    async def update_user_lesson(
        self, user_id: int, lesson_id: int, update_data: dict
    ) -> UserLesson:
        """
        Update user lesson progress.

        Args:
            user_id: ID of the user
            lesson_id: ID of the lesson
            update_data: Dictionary of fields to update

        Returns:
            Updated UserLesson object

        Raises:
            HTTPException: If user lesson not found
        """
        user_lesson = await self.repository.get_by_user_and_lesson(user_id, lesson_id)

        if not user_lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User lesson not found",
            )

        # Update only provided fields
        for field, value in update_data.items():
            if value is not None and hasattr(user_lesson, field):
                setattr(user_lesson, field, value)

        # Update timestamp
        user_lesson.updated_at = datetime.now(timezone.utc)

        return await self.repository.update(user_lesson)

    async def unlock_lesson(self, user_id: int, lesson_id: int) -> UserLesson:
        """
        Unlock a lesson for a user.

        Args:
            user_id: ID of the user
            lesson_id: ID of the lesson

        Returns:
            Updated UserLesson object
        """
        return await self.update_user_lesson(
            user_id=user_id,
            lesson_id=lesson_id,
            update_data={"is_lesson_unlocked": True},
        )

    async def unlock_audio(self, user_id: int, lesson_id: int) -> UserLesson:
        """
        Unlock audio for a lesson.

        Args:
            user_id: ID of the user
            lesson_id: ID of the lesson

        Returns:
            Updated UserLesson object
        """
        return await self.update_user_lesson(
            user_id=user_id,
            lesson_id=lesson_id,
            update_data={"is_audio_unlocked": True},
        )

    async def complete_quiz(self, user_id: int, lesson_id: int) -> UserLesson:
        """
        Mark quiz as completed for a lesson.

        Args:
            user_id: ID of the user
            lesson_id: ID of the lesson

        Returns:
            Updated UserLesson object
        """
        return await self.update_user_lesson(
            user_id=user_id,
            lesson_id=lesson_id,
            update_data={"is_quiz_completed": True},
        )

    async def complete_lesson(self, user_id: int, lesson_id: int) -> UserLesson:
        """
        Mark a lesson as completed for a user.

        Args:
            user_id: ID of the user
            lesson_id: ID of the lesson

        Returns:
            Updated UserLesson object
        """
        # Fetch lesson to check if it has a quiz
        lesson = await self.lesson_repo.get_by_id(lesson_id)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        if lesson.has_quiz:
            # Check if user has completed the quiz
            user_lesson = await self.repository.get_by_user_and_lesson(
                user_id, lesson_id
            )
            if not user_lesson:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User lesson progress not found",
                )

            if not user_lesson.is_quiz_completed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You must complete the lesson quiz before marking the lesson as completed.",
                )

        return await self.update_user_lesson(
            user_id=user_id,
            lesson_id=lesson_id,
            update_data={"status": ProgressStatus.COMPLETED},
        )
