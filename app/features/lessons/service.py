"""Service for managing lessons."""

from fastapi import HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.features.lessons.repository import (
    LessonRepository,
    UserLessonRepository,
    LessonAudioRepository,
)
from app.features.lessons.models import Lesson, UserLesson, LessonAudio
from app.features.courses.models import ProgressStatus
from app.features.lessons.generation_service import lesson_generation_service
from app.features.modules.repository import ModuleRepository, UserModuleRepository
from app.features.modules.service import UserModuleService
from app.features.courses.repository import CourseRepository, UserCourseRepository
from app.features.lessons.lecture_service import lecture_conversion_service
from app.services.audio_generation_service import audio_generation_service
from app.services.storage_service import firebase_storage_service


class LessonService:
    """Service for lesson business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = LessonRepository(session)
        self.audio_repo = LessonAudioRepository(session)
        self.user_lesson_repo = UserLessonRepository(session)
        self.course_repo = CourseRepository(session)
        self.module_repo = ModuleRepository(session)
        self.generation_service = lesson_generation_service

    async def get_lesson_audios(
        self, user_id: int, lesson_id: int
    ) -> List[LessonAudio]:
        """
        Get all audios for a lesson, restricted by user access.

        Access is granted only if:
        1. User has a UserLesson record
        2. Audio is unlocked for that user (is_audio_unlocked = True)

        Args:
            user_id: ID of the user requesting
            lesson_id: ID of the lesson

        Returns:
            List of LessonAudio records

        Raises:
            HTTPException: If access is denied or lesson not found
        """
        # 1. Check if user has access to this lesson's audio
        user_lesson = await self.user_lesson_repo.get_by_user_and_lesson(
            user_id, lesson_id
        )

        if not user_lesson:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You have not started this lesson yet.",
            )

        if not user_lesson.is_audio_unlocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Audio is locked for this lesson. Please unlock it first.",
            )

        # 2. Fetch and return audios
        return await self.audio_repo.get_by_lesson_id(lesson_id)

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

    async def generate_audio_from_content(self, lesson_id: int) -> List[LessonAudio]:
        """
        Generate audio from lesson content in multiple parts.

        Converts lesson content into lecture script parts, generates audio for each part,
        uploads to storage, and inserts records into the lesson_audios table.

        Args:
            lesson_id: ID of the lesson

        Returns:
            List of created LessonAudio records, or empty list if generation failed
        """
        lesson = await self.get_lesson_by_id(lesson_id)
        if not lesson or not lesson.content:
            return []

        # Generate lecture script parts
        lecture_parts = await lecture_conversion_service.generate_lecture_parts(
            lesson.content,
            max_parts=4,
        )

        if not lecture_parts:
            return []

        created_audios: List[LessonAudio] = []

        for part in lecture_parts:
            try:
                # Generate audio bytes in MP3 format for this part
                audio_bytes = await audio_generation_service.generate_audio_mp3(
                    text=part.script, sample_rate=24000, bitrate="128k"
                )

                # Upload to Firebase with descriptive folder structure
                audio_url = firebase_storage_service.upload_audio(
                    audio_data=audio_bytes,
                    folder=f"lesson_audio/{lesson_id}",
                )

                # Create LessonAudio record
                lesson_audio = LessonAudio(
                    lesson_id=lesson_id,
                    title=part.title,
                    script=part.script,
                    audio_url=audio_url,
                    order=part.order,
                )

                created_audio = await self.audio_repo.create(lesson_audio)
                await self.session.commit()
                created_audios.append(created_audio)

                print(
                    f"✓ Generated audio part {part.order}: {part.title} ({len(part.script.split())} words)"
                )

            except Exception as e:
                print(f"✗ Failed to generate audio for part {part.order}: {e}")
                # Continue with other parts even if one fails
                continue

        print(f"Generated {len(created_audios)} audio parts for lesson {lesson_id}")

        return created_audios

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
            if not existing.is_lesson_unlocked:
                existing.is_lesson_unlocked = True
                existing.updated_at = datetime.now(timezone.utc)
                await self.repository.update(existing)
            return existing

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
            is_lesson_unlocked=True,  # Auto-unlock on start
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
        # Verify lesson exists
        lesson = await self.lesson_repo.get_by_id(lesson_id)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        user_lesson = await self.update_user_lesson(
            user_id=user_id,
            lesson_id=lesson_id,
            update_data={"status": ProgressStatus.COMPLETED},
        )

        # Check if this was the last lesson in the module and complete it
        await self.user_module_service.check_and_complete_module(
            user_id=user_id, module_id=lesson.module_id
        )

        return user_lesson
