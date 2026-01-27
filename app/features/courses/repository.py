"""Course repository for database operations."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col
from app.features.courses.models import Course, UserCourse, Category, SubCategory


class CourseRepository:
    """Repository for course database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, course_id: int) -> Optional[Course]:
        """Get course by ID."""
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(Course)
            .where(Course.id == course_id)
            .options(selectinload(Course.category), selectinload(Course.sub_category))  # type: ignore
        )
        return result.scalar_one_or_none()

    async def get_with_modules(self, course_id: int) -> Optional[Course]:
        """Get course by ID with modules and lessons eagerly loaded."""
        from sqlalchemy.orm import selectinload
        from app.features.modules.models import Module

        result = await self.session.execute(
            select(Course)
            .where(Course.id == course_id)
            .options(
                selectinload(Course.modules).selectinload(Module.lessons),  # type: ignore
                selectinload(Course.category),  # type: ignore
                selectinload(Course.sub_category),  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Course]:
        """Get all courses for a specific user."""
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(Course)
            .where(Course.user_id == user_id)
            .options(selectinload(Course.category), selectinload(Course.sub_category))  # type: ignore
            .offset(skip)
            .limit(limit)
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
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(Course)
            .options(selectinload(Course.category), selectinload(Course.sub_category))  # type: ignore
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_with_filters(
        self,
        skip: int = 0,
        limit: int = 100,
        is_public: Optional[bool] = None,
        level: Optional[str] = None,
        category_id: Optional[int] = None,
        sub_category_id: Optional[int] = None,
        min_enrollees: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Course]:
        """Get all courses with pagination and optional filters."""
        from sqlalchemy.orm import selectinload

        query = select(Course).options(
            selectinload(Course.category), selectinload(Course.sub_category)  # type: ignore
        )

        # Apply filters
        if is_public is not None:
            query = query.where(Course.is_public == is_public)

        if level is not None:
            query = query.where(Course.level == level)

        if min_enrollees is not None:
            query = query.where(Course.total_enrollees >= min_enrollees)

        if category_id is not None:
            query = query.where(Course.category_id == category_id)

        if sub_category_id is not None:
            query = query.where(Course.sub_category_id == sub_category_id)

        if search:
            query = query.where(col(Course.title).contains(search))

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
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        level: Optional[str] = None,
    ) -> List[UserCourse]:
        """Get all user courses with course details eagerly loaded."""
        from sqlalchemy.orm import selectinload

        query = (
            select(UserCourse)
            .where(UserCourse.user_id == user_id)
            .options(
                selectinload(UserCourse.course).selectinload(Course.category),  # type: ignore
                selectinload(UserCourse.course).selectinload(Course.sub_category),  # type: ignore
            )
        )

        if search:
            query = query.join(Course).where(col(Course.title).contains(search))

        if level:
            # If not already joined by search
            if not search:
                query = query.join(Course)
            query = query.where(Course.level == level)

        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id_with_course(self, user_course_id: int) -> Optional[UserCourse]:
        """Get user course by ID with course details eagerly loaded."""
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(UserCourse)
            .where(UserCourse.id == user_course_id)
            .options(
                selectinload(UserCourse.course).selectinload(Course.category),  # type: ignore
                selectinload(UserCourse.course).selectinload(Course.sub_category),  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_course_with_details(
        self, user_id: int, course_id: int
    ) -> Optional[UserCourse]:
        """Get user course by user ID and course ID with course details eagerly loaded."""
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(UserCourse)
            .where(UserCourse.user_id == user_id)
            .where(UserCourse.course_id == course_id)
            .options(
                selectinload(UserCourse.course).selectinload(Course.category),  # type: ignore
                selectinload(UserCourse.course).selectinload(Course.sub_category),  # type: ignore
            )
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


class CategoryRepository:
    """Repository for category database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, skip: int = 0, limit: int = 100) -> List["Category"]:
        """Get all categories."""
        from app.features.courses.models import Category

        result = await self.session.execute(select(Category).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_by_id(self, category_id: int) -> Optional["Category"]:
        """Get category by ID."""
        from app.features.courses.models import Category

        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional["Category"]:
        """Get category by name."""
        from app.features.courses.models import Category

        result = await self.session.execute(
            select(Category).where(Category.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, category: "Category") -> "Category":
        """Create a new category."""
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def update(self, category: "Category") -> "Category":
        """Update an existing category."""
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def delete(self, category: "Category") -> None:
        """Delete a category."""
        await self.session.delete(category)
        await self.session.flush()


class SubCategoryRepository:
    """Repository for sub-category database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, skip: int = 0, limit: int = 100) -> List["SubCategory"]:
        """Get all sub-categories."""
        from app.features.courses.models import SubCategory

        result = await self.session.execute(
            select(SubCategory).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, sub_category_id: int) -> Optional["SubCategory"]:
        """Get sub-category by ID."""
        from app.features.courses.models import SubCategory

        result = await self.session.execute(
            select(SubCategory).where(SubCategory.id == sub_category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_category_id(
        self, category_id: int, skip: int = 0, limit: int = 100
    ) -> List["SubCategory"]:
        """Get sub-categories by category ID."""
        from app.features.courses.models import SubCategory

        result = await self.session.execute(
            select(SubCategory)
            .where(SubCategory.category_id == category_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Optional["SubCategory"]:
        """Get sub-category by name."""
        from app.features.courses.models import SubCategory

        result = await self.session.execute(
            select(SubCategory).where(SubCategory.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, sub_category: "SubCategory") -> "SubCategory":
        """Create a new sub-category."""
        self.session.add(sub_category)
        await self.session.flush()
        await self.session.refresh(sub_category)
        return sub_category

    async def update(self, sub_category: "SubCategory") -> "SubCategory":
        """Update an existing sub-category."""
        self.session.add(sub_category)
        await self.session.flush()
        await self.session.refresh(sub_category)
        return sub_category

    async def delete(self, sub_category: "SubCategory") -> None:
        """Delete a sub-category."""
        await self.session.delete(sub_category)
        await self.session.flush()
