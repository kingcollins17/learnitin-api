"""Course repository for database operations."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.features.courses.models import Course, UserCourse


class CourseRepository:
    """Repository for course database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, course_id: int) -> Optional[Course]:
        """Get course by ID."""
        result = await self.session.execute(
            select(Course).where(Course.id == course_id)
        )
        return result.scalar_one_or_none()

    async def get_with_modules(self, course_id: int) -> Optional[Course]:
        """Get course by ID with modules and lessons eagerly loaded."""
        from sqlalchemy.orm import selectinload
        from app.features.modules.models import Module

        result = await self.session.execute(
            select(Course)
            .where(Course.id == course_id)
            .options(selectinload(Course.modules).selectinload(Module.lessons))  # type: ignore
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Course]:
        """Get all courses for a specific user."""
        result = await self.session.execute(
            select(Course).where(Course.user_id == user_id).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, course: Course) -> Course:
        """Create a new course."""
        self.session.add(course)
        await self.session.flush()
        await self.session.refresh(course)
        return course

    async def update(self, course: Course) -> Course:
        """Update an existing course."""
        self.session.add(course)
        await self.session.flush()
        await self.session.refresh(course)
        return course

    async def delete(self, course: Course) -> None:
        """Delete a course."""
        await self.session.delete(course)
        await self.session.commit()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Course]:
        """Get all courses with pagination."""
        result = await self.session.execute(select(Course).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_all_with_filters(
        self,
        skip: int = 0,
        limit: int = 100,
        is_public: Optional[bool] = None,
        level: Optional[str] = None,
        min_enrollees: Optional[int] = None,
    ) -> List[Course]:
        """Get all courses with pagination and optional filters."""
        query = select(Course)

        # Apply filters
        if is_public is not None:
            query = query.where(Course.is_public == is_public)

        if level is not None:
            query = query.where(Course.level == level)

        if min_enrollees is not None:
            query = query.where(Course.total_enrollees >= min_enrollees)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())


class UserCourseRepository:
    """Repository for user course database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_course_id: int) -> Optional[UserCourse]:
        """Get user course by ID."""
        result = await self.session.execute(
            select(UserCourse).where(UserCourse.id == user_course_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_course(
        self, user_id: int, course_id: int
    ) -> Optional[UserCourse]:
        """Get user course by user ID and course ID."""
        result = await self.session.execute(
            select(UserCourse)
            .where(UserCourse.user_id == user_id)
            .where(UserCourse.course_id == course_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[UserCourse]:
        """Get all courses for a specific user."""
        result = await self.session.execute(
            select(UserCourse)
            .where(UserCourse.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user_with_course(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[UserCourse]:
        """Get all user courses with course details eagerly loaded."""
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(UserCourse)
            .where(UserCourse.user_id == user_id)
            .options(selectinload("course"))  # type: ignore
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id_with_course(self, user_course_id: int) -> Optional[UserCourse]:
        """Get user course by ID with course details eagerly loaded."""
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(UserCourse)
            .where(UserCourse.id == user_course_id)
            .options(selectinload("course"))  # type: ignore
        )
        return result.scalar_one_or_none()

    async def create(self, user_course: UserCourse) -> UserCourse:
        """Create a new user course record."""
        self.session.add(user_course)
        await self.session.flush()
        await self.session.refresh(user_course)
        return user_course

    async def update(self, user_course: UserCourse) -> UserCourse:
        """Update an existing user course record."""
        self.session.add(user_course)
        await self.session.flush()
        await self.session.refresh(user_course)
        return user_course

    async def delete(self, user_course: UserCourse) -> None:
        """Delete a user course record."""
        await self.session.delete(user_course)
        await self.session.flush()
