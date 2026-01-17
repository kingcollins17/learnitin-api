"""Lesson repository for database operations."""

from typing import Optional, List
import json
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from app.features.lessons.models import Lesson, UserLesson, LessonAudio


class LessonRepository:
    """Repository for lesson database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, lesson_id: int) -> Optional[Lesson]:
        """Get lesson by ID."""
        result = await self.session.execute(
            select(Lesson)
            .where(Lesson.id == lesson_id)
            .options(selectinload(Lesson.audios))
        )
        return result.scalar_one_or_none()

    async def get_by_module_id(
        self, module_id: int, skip: int = 0, limit: int = 100
    ) -> List[Lesson]:
        """Get all lessons for a specific module."""
        result = await self.session.execute(
            select(Lesson)
            .where(Lesson.module_id == module_id)
            .order_by(Lesson.order)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_previous_lesson(
        self, module_id: int, current_order: int
    ) -> Optional[Lesson]:
        """Get the lesson immediately before the current one in the same module."""
        result = await self.session.execute(
            select(Lesson)
            .where(Lesson.module_id == module_id)
            .where(Lesson.order < current_order)
            .order_by(desc(Lesson.order))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_course_id(
        self, course_id: int, skip: int = 0, limit: int = 100
    ) -> List[Lesson]:
        """Get all lessons for a specific course."""
        result = await self.session.execute(
            select(Lesson)
            .where(Lesson.course_id == course_id)
            .order_by(Lesson.module_id, Lesson.order)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, lesson: Lesson) -> Lesson:
        """Create a new lesson."""
        self.session.add(lesson)
        await self.session.flush()
        await self.session.refresh(lesson)
        return lesson

    async def update(self, lesson: Lesson) -> Lesson:
        """Update an existing lesson."""
        self.session.add(lesson)
        await self.session.flush()
        await self.session.refresh(lesson)
        return lesson

    async def delete(self, lesson: Lesson) -> None:
        """Delete a lesson."""
        await self.session.delete(lesson)
        await self.session.flush()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Lesson]:
        """Get all lessons with pagination."""
        result = await self.session.execute(
            select(Lesson)
            .order_by(Lesson.course_id, Lesson.module_id, Lesson.order)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


class UserLessonRepository:
    """Repository for user lesson database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_lesson_id: int) -> Optional[UserLesson]:
        """Get user lesson by ID."""
        result = await self.session.execute(
            select(UserLesson).where(UserLesson.id == user_lesson_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_lesson(
        self, user_id: int, lesson_id: int
    ) -> Optional[UserLesson]:
        """Get user lesson by user ID and lesson ID."""
        result = await self.session.execute(
            select(UserLesson)
            .where(UserLesson.user_id == user_id)
            .where(UserLesson.lesson_id == lesson_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_module(
        self, user_id: int, module_id: int
    ) -> List[UserLesson]:
        """Get all user lessons for a specific module."""
        result = await self.session.execute(
            select(UserLesson)
            .where(UserLesson.user_id == user_id)
            .where(UserLesson.module_id == module_id)
        )
        return list(result.scalars().all())

    async def get_by_user_and_course(
        self, user_id: int, course_id: int
    ) -> List[UserLesson]:
        """Get all user lessons for a specific course."""
        result = await self.session.execute(
            select(UserLesson)
            .where(UserLesson.user_id == user_id)
            .where(UserLesson.course_id == course_id)
        )
        return list(result.scalars().all())

    async def create(self, user_lesson: UserLesson) -> UserLesson:
        """Create a new user lesson record."""
        self.session.add(user_lesson)
        await self.session.flush()
        await self.session.refresh(user_lesson)
        return user_lesson

    async def update(self, user_lesson: UserLesson) -> UserLesson:
        """Update an existing user lesson record."""
        self.session.add(user_lesson)
        await self.session.flush()
        await self.session.refresh(user_lesson)
        return user_lesson

    async def delete(self, user_lesson: UserLesson) -> None:
        """Delete a user lesson record."""
        await self.session.delete(user_lesson)
        await self.session.flush()


class LessonAudioRepository:
    """Repository for lesson audio database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, audio_id: int) -> Optional[LessonAudio]:
        """Get lesson audio by ID."""
        result = await self.session.execute(
            select(LessonAudio).where(LessonAudio.id == audio_id)
        )
        return result.scalar_one_or_none()

    async def get_by_lesson_id(
        self, lesson_id: int, skip: int = 0, limit: int = 100
    ) -> List[LessonAudio]:
        """Get all audios for a specific lesson."""
        result = await self.session.execute(
            select(LessonAudio)
            .where(LessonAudio.lesson_id == lesson_id)
            .order_by(LessonAudio.order)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[LessonAudio]:
        """Get all lesson audios with pagination."""
        result = await self.session.execute(
            select(LessonAudio)
            .order_by(LessonAudio.lesson_id, LessonAudio.order)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, audio: LessonAudio) -> LessonAudio:
        """Create a new lesson audio."""
        self.session.add(audio)
        await self.session.flush()
        await self.session.refresh(audio)
        return audio

    async def update(self, audio: LessonAudio) -> LessonAudio:
        """Update an existing lesson audio."""
        self.session.add(audio)
        await self.session.flush()
        await self.session.refresh(audio)
        return audio

    async def update_with(
        self, audio_id: int, update_data: dict
    ) -> Optional[LessonAudio]:
        """Update a lesson audio by ID with a dictionary of values."""
        audio = await self.get_by_id(audio_id)
        if not audio:
            return None

        for key, value in update_data.items():
            if hasattr(audio, key):
                setattr(audio, key, value)

        return await self.update(audio)

    async def delete(self, audio: LessonAudio) -> None:
        """Delete a lesson audio."""
        await self.session.delete(audio)
        await self.session.flush()
