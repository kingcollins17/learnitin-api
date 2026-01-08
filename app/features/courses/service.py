"""Course business logic and service layer."""

from fastapi import HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.courses.repository import CourseRepository
from app.features.courses.schemas import (
    CourseOutline,
    CourseResponse,
)
from app.features.courses.models import Course, UserCourse, LearningPace, CourseLevel
from app.features.modules.models import Module
from app.features.lessons.models import Lesson
from app.features.modules.repository import ModuleRepository
from app.features.lessons.repository import LessonRepository
from app.features.courses.repository import UserCourseRepository
import json
import re


class CourseService:
    """Service for course business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = CourseRepository(session)
        self.module_repository = ModuleRepository(session)
        self.lesson_repository = LessonRepository(session)
        self.user_course_repository = UserCourseRepository(session)

    async def create_course(self, user_id: int, course_data: CourseOutline) -> Course:
        """
        Create a new course from a course outline.

        Args:
            user_id: ID of the user creating the course
            course_data: Course outline containing modules and lessons

        Returns:
            Created Course object
        """
        # 1. Create Course
        course = Course(
            user_id=user_id,
            title=course_data.title,
            description=course_data.description,
            duration=course_data.duration,
            is_public=False,  # Default to private
            learning_pace=LearningPace.BALANCED,  # Default values
            level=CourseLevel.BEGINNER,
        )
        course = await self.repository.create(course)

        # 2. Create Modules and Lessons
        for i, module_data in enumerate(course_data.outline):
            # Create Module
            slug = self._create_slug(module_data.title)
            module = Module(
                course_id=course.id,
                title=module_data.title,
                description=module_data.description,
                module_slug=f"{slug}-{i+1}",  # Ensure uniqueness with index
                objectives=json.dumps(
                    []
                ),  # Default empty list for now as it's not in ModuleOverview
                order=i,
            )
            module = await self.module_repository.create(module)

            # Create Lessons for this Module
            for j, lesson_data in enumerate(module_data.lessons):
                lesson = Lesson(
                    course_id=course.id,
                    module_id=module.id,
                    title=lesson_data.title,
                    description=f"Duration: {lesson_data.duration}",
                    objectives=json.dumps(lesson_data.objectives),
                    credit_cost=lesson_data.credit_cost,
                    order=j,
                )
                await self.lesson_repository.create(lesson)

        return course

    async def enroll_course(self, user_id: int, course_id: int) -> UserCourse:
        """
        Enroll a user in a course.

        Args:
            user_id: ID of the user to enroll
            course_id: ID of the course to enroll in

        Returns:
            Created UserCourse object

        Raises:
            HTTPException: If user is already enrolled
        """
        # Check if already enrolled
        existing_enrollment = await self.user_course_repository.get_by_user_and_course(
            user_id=user_id, course_id=course_id
        )

        if existing_enrollment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already enrolled in this course",
            )

        # Create enrollment
        user_course = UserCourse(user_id=user_id, course_id=course_id)
        user_course = await self.user_course_repository.create(user_course)

        # Increment total_enrollees
        course = await self.repository.get_by_id(course_id)
        if course:
            course.total_enrollees += 1
            await self.repository.update(course)

        return user_course

    def _create_slug(self, text: str) -> str:
        """Create a URL-friendly slug from text."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s-]", "", text)
        text = re.sub(r"\s+", "-", text)
        return text

    async def get_courses(
        self,
        page: int = 1,
        per_page: int = 10,
        is_public: Optional[bool] = None,
        level: Optional[str] = None,
        min_enrollees: Optional[int] = None,
    ) -> List[Course]:
        """
        Get all courses with pagination and filters.

        Args:
            page: Page number (1-indexed)
            per_page: Number of items per page
            is_public: Filter by public/private courses
            level: Filter by course level
            min_enrollees: Filter by minimum number of enrollees

        Returns:
            List of courses matching the filters
        """
        skip = (page - 1) * per_page
        return await self.repository.get_all_with_filters(
            skip=skip,
            limit=per_page,
            is_public=is_public,
            level=level,
            min_enrollees=min_enrollees,
        )

    async def get_course_detail(self, course_id: int) -> Optional[Course]:
        """
        Get course detail with all modules and lessons.

        Args:
            course_id: ID of the course

        Returns:
            Course with modules and lessons, or None if not found
        """
        return await self.repository.get_with_modules(course_id)

    async def get_user_courses(
        self, user_id: int, page: int = 1, per_page: int = 10
    ) -> List[UserCourse]:
        """
        Get all courses enrolled by a user.

        Args:
            user_id: ID of the user
            page: Page number (1-indexed)
            per_page: Number of items per page

        Returns:
            List of user courses with course details
        """
        skip = (page - 1) * per_page
        return await self.user_course_repository.get_by_user_with_course(
            user_id=user_id, skip=skip, limit=per_page
        )

    async def get_user_course_detail(
        self, user_id: int, user_course_id: int
    ) -> Optional[UserCourse]:
        """
        Get user course detail.

        Args:
            user_id: ID of the user
            user_course_id: ID of the user course

        Returns:
            UserCourse with course details, or None if not found

        Raises:
            HTTPException: If user course not found or doesn't belong to user
        """
        user_course = await self.user_course_repository.get_by_id_with_course(
            user_course_id
        )

        if not user_course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User course not found",
            )

        if user_course.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this course",
            )

        return user_course

    async def update_course(
        self, user_id: int, course_id: int, course_update: dict
    ) -> Course:
        """
        Update a course.

        Args:
            user_id: ID of the user attempting to update
            course_id: ID of the course to update
            course_update: Dictionary of fields to update

        Returns:
            Updated Course object

        Raises:
            HTTPException: If course not found or user is not the creator
        """
        course = await self.repository.get_by_id(course_id)

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Only the course creator can update it
        if course.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this course",
            )

        # Update only provided fields
        from datetime import datetime, timezone

        for field, value in course_update.items():
            if value is not None and hasattr(course, field):
                setattr(course, field, value)

        # Update timestamp
        course.updated_at = datetime.now(timezone.utc)

        return await self.repository.update(course)

    async def delete_course(self, user_id: int, course_id: int) -> None:
        """
        Delete a course.

        Args:
            user_id: ID of the user attempting to delete
            course_id: ID of the course to delete

        Raises:
            HTTPException: If course not found or user is not the creator
        """
        course = await self.repository.get_by_id(course_id)

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Only the course creator can delete it
        if course.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this course",
            )

        await self.repository.delete(course)
