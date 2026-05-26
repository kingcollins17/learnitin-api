"""Course repository for database operations."""

from typing import Optional, List
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, col
from app.features.courses.models import Course, UserCourse, Category, SubCategory
from app.features.modules.models import Module
from app.common.cache import cache_service

# Cache namespaces for courses
COURSE_BY_ID_CACHE = "course_by_id"
COURSE_WITH_MODULES_CACHE = "course_with_modules"
COURSE_LIST_ALL_CACHE = "course_list_all"
COURSE_LIST_BY_USER_CACHE = "course_list_by_user"
COURSE_LIST_ORPHANED_CACHE = "course_list_orphaned"
COURSE_LIST_FILTERED_CACHE = "course_list_filtered"

# Cache namespaces for categories
CATEGORY_BY_ID_CACHE = "category_by_id"
CATEGORY_BY_NAME_CACHE = "category_by_name"
CATEGORY_LIST_ALL_CACHE = "category_list_all"

# Cache namespaces for user courses
USER_COURSE_BY_ID_CACHE = "user_course_by_id"
USER_COURSE_BY_ID_WITH_COURSE_CACHE = "user_course_by_id_with_course"
USER_COURSE_BY_USER_AND_COURSE_CACHE = "user_course_by_user_and_course"
USER_COURSE_BY_USER_AND_COURSE_DETAILS_CACHE = "user_course_by_user_and_course_with_details"
USER_COURSE_LIST_BY_USER_CACHE = "user_course_list_by_user"
USER_COURSE_LIST_BY_USER_WITH_COURSE_CACHE = "user_course_list_by_user_with_course"

cache_service.register(COURSE_BY_ID_CACHE, maxsize=4096, ttl=60)
cache_service.register(COURSE_WITH_MODULES_CACHE, maxsize=4096, ttl=60)
cache_service.register(COURSE_LIST_ALL_CACHE, maxsize=1024, ttl=60)
cache_service.register(COURSE_LIST_BY_USER_CACHE, maxsize=1024, ttl=60)
cache_service.register(COURSE_LIST_ORPHANED_CACHE, maxsize=1024, ttl=60)
cache_service.register(COURSE_LIST_FILTERED_CACHE, maxsize=1024, ttl=60)

cache_service.register(CATEGORY_BY_ID_CACHE, maxsize=1024, ttl=60)
cache_service.register(CATEGORY_BY_NAME_CACHE, maxsize=1024, ttl=60)
cache_service.register(CATEGORY_LIST_ALL_CACHE, maxsize=1024, ttl=60)

cache_service.register(USER_COURSE_BY_ID_CACHE, maxsize=4096, ttl=60)
cache_service.register(USER_COURSE_BY_ID_WITH_COURSE_CACHE, maxsize=4096, ttl=60)
cache_service.register(USER_COURSE_BY_USER_AND_COURSE_CACHE, maxsize=4096, ttl=60)
cache_service.register(USER_COURSE_BY_USER_AND_COURSE_DETAILS_CACHE, maxsize=4096, ttl=60)
cache_service.register(USER_COURSE_LIST_BY_USER_CACHE, maxsize=4096, ttl=60)
cache_service.register(USER_COURSE_LIST_BY_USER_WITH_COURSE_CACHE, maxsize=4096, ttl=60)



class CourseRepository:
    """Repository for course database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def count(self) -> int:
        """Count all courses."""
        query = select(func.count()).select_from(Course)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_by_id(self, course_id: int, *, use_cache: bool = True) -> Optional[Course]:
        """Get course by ID."""
        if use_cache:
            cached = cache_service.get(COURSE_BY_ID_CACHE, course_id)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(Course)
            .where(Course.id == course_id)
            .options(selectinload(Course.category), selectinload(Course.sub_category))  # type: ignore
        )
        course = result.scalar_one_or_none()
        if course is not None:
            cache_service.set(COURSE_BY_ID_CACHE, course_id, course)
        return course

    async def get_with_modules(self, course_id: int, *, use_cache: bool = True) -> Optional[Course]:
        """Get course by ID with modules and lessons eagerly loaded."""
        if use_cache:
            cached = cache_service.get(COURSE_WITH_MODULES_CACHE, course_id)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(Course)
            .where(Course.id == course_id)
            .options(
                selectinload(Course.modules).selectinload(Module.lessons),  # type: ignore
                selectinload(Course.category),  # type: ignore
                selectinload(Course.sub_category),  # type: ignore
            )
        )
        course = result.scalar_one_or_none()
        if course is not None:
            cache_service.set(COURSE_WITH_MODULES_CACHE, course_id, course)
        return course

    async def get_by_user_id(
        self, user_id: int, skip: int = 0, limit: int = 100, *, use_cache: bool = True
    ) -> List[Course]:
        """Get all courses for a specific user."""
        cache_key = (user_id, skip, limit)
        if use_cache:
            cached = cache_service.get(COURSE_LIST_BY_USER_CACHE, cache_key)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(Course)
            .where(Course.user_id == user_id)
            .options(selectinload(Course.category), selectinload(Course.sub_category))  # type: ignore
            .offset(skip)
            .limit(limit)
        )
        courses = list(result.scalars().all())
        cache_service.set(COURSE_LIST_BY_USER_CACHE, cache_key, courses)
        return courses

    async def create(self, course: Course) -> Course:
        """Create a new course."""
        self.session.add(course)
        await self.session.flush()
        await self.session.refresh(course)

        # Invalidate list caches
        self.invalidate_cache(course.id)

        return course

    async def update(self, course: Course) -> Course:
        """Update an existing course."""
        self.session.add(course)
        await self.session.flush()
        await self.session.refresh(course)

        # Invalidate course caches
        self.invalidate_cache(course.id)

        return course

    async def delete(self, course: Course) -> None:
        """Delete a course."""
        course_id = course.id
        await self.session.delete(course)
        await self.session.commit()

        # Invalidate course caches
        self.invalidate_cache(course_id)

    @staticmethod
    def invalidate_cache(course_id: int) -> None:
        """Manually invalidate the course caches.

        Args:
            course_id: The ID of the course to invalidate.
        """
        cache_service.delete(COURSE_BY_ID_CACHE, course_id)
        cache_service.delete(COURSE_WITH_MODULES_CACHE, course_id)
        cache_service.clear(COURSE_LIST_ALL_CACHE)
        cache_service.clear(COURSE_LIST_BY_USER_CACHE)
        cache_service.clear(COURSE_LIST_ORPHANED_CACHE)
        cache_service.clear(COURSE_LIST_FILTERED_CACHE)

    async def get_all(self, skip: int = 0, limit: int = 100, *, use_cache: bool = True) -> List[Course]:
        """Get all courses with pagination."""
        cache_key = (skip, limit)
        if use_cache:
            cached = cache_service.get(COURSE_LIST_ALL_CACHE, cache_key)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(Course)
            .options(selectinload(Course.category), selectinload(Course.sub_category))  # type: ignore
            .offset(skip)
            .limit(limit)
        )
        courses = list(result.scalars().all())
        cache_service.set(COURSE_LIST_ALL_CACHE, cache_key, courses)
        return courses

    async def get_orphaned_courses(self, *, use_cache: bool = True) -> List[Course]:
        """Get courses that have no creator (user_id is NULL) and are not public."""
        cache_key = "orphaned"
        if use_cache:
            cached = cache_service.get(COURSE_LIST_ORPHANED_CACHE, cache_key)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(Course)
            .where(Course.user_id == None)
            .where(Course.is_public == False)
        )
        courses = list(result.scalars().all())
        cache_service.set(COURSE_LIST_ORPHANED_CACHE, cache_key, courses)
        return courses

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
        *,
        use_cache: bool = True,
    ) -> List[Course]:
        """Get all courses with pagination and optional filters."""
        cache_key = (skip, limit, is_public, level, category_id, sub_category_id, min_enrollees, search)
        if use_cache:
            cached = cache_service.get(COURSE_LIST_FILTERED_CACHE, cache_key)
            if cached is not None:
                return cached

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

        # Apply ordering
        query = query.order_by(col(Course.total_enrollees).desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        courses = list(result.scalars().all())
        cache_service.set(COURSE_LIST_FILTERED_CACHE, cache_key, courses)
        return courses


class UserCourseRepository:
    """Repository for user course database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_course_id: int, *, use_cache: bool = True) -> Optional[UserCourse]:
        """Get user course by ID."""
        if use_cache:
            cached = cache_service.get(USER_COURSE_BY_ID_CACHE, user_course_id)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(UserCourse).where(UserCourse.id == user_course_id)
        )
        user_course = result.scalar_one_or_none()
        if user_course is not None:
            cache_service.set(USER_COURSE_BY_ID_CACHE, user_course_id, user_course)
        return user_course

    async def get_by_user_and_course(
        self, user_id: int, course_id: int, *, use_cache: bool = True
    ) -> Optional[UserCourse]:
        """Get user course by user ID and course ID."""
        cache_key = (user_id, course_id)
        if use_cache:
            cached = cache_service.get(USER_COURSE_BY_USER_AND_COURSE_CACHE, cache_key)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(UserCourse)
            .where(UserCourse.user_id == user_id)
            .where(UserCourse.course_id == course_id)
        )
        user_course = result.scalar_one_or_none()
        if user_course is not None:
            cache_service.set(USER_COURSE_BY_USER_AND_COURSE_CACHE, cache_key, user_course)
        return user_course

    async def get_by_user(
        self, user_id: int, skip: int = 0, limit: int = 100, *, use_cache: bool = True
    ) -> List[UserCourse]:
        """Get all courses for a specific user."""
        cache_key = (user_id, skip, limit)
        if use_cache:
            cached = cache_service.get(USER_COURSE_LIST_BY_USER_CACHE, cache_key)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(UserCourse)
            .where(UserCourse.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        courses = list(result.scalars().all())
        cache_service.set(USER_COURSE_LIST_BY_USER_CACHE, cache_key, courses)
        return courses

    async def get_by_user_with_course(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        level: Optional[str] = None,
        *,
        use_cache: bool = True,
    ) -> List[UserCourse]:
        """Get all user courses with course details eagerly loaded."""
        cache_key = (user_id, skip, limit, search, level)
        if use_cache:
            cached = cache_service.get(USER_COURSE_LIST_BY_USER_WITH_COURSE_CACHE, cache_key)
            if cached is not None:
                return cached

        query = (
            select(UserCourse)
            .where(UserCourse.user_id == user_id)
            .options(
                selectinload(UserCourse.course).selectinload(Course.category),  # type: ignore
                selectinload(UserCourse.course).selectinload(Course.sub_category),  # type: ignore
                selectinload(UserCourse.course).selectinload(Course.modules),  # type: ignore
            )
        )

        if search:
            query = query.join(Course).where(col(Course.title).contains(search))

        if level:
            # If not already joined by search
            if not search:
                query = query.join(Course)
            query = query.where(Course.level == level)

        # Apply ordering
        query = query.order_by(
            col(UserCourse.updated_at).desc(), col(UserCourse.created_at).desc()
        )

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        courses = list(result.scalars().all())
        cache_service.set(USER_COURSE_LIST_BY_USER_WITH_COURSE_CACHE, cache_key, courses)
        return courses

    async def get_by_id_with_course(self, user_course_id: int, *, use_cache: bool = True) -> Optional[UserCourse]:
        """Get user course by ID with course details eagerly loaded."""
        if use_cache:
            cached = cache_service.get(USER_COURSE_BY_ID_WITH_COURSE_CACHE, user_course_id)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(UserCourse)
            .where(UserCourse.id == user_course_id)
            .options(
                selectinload(UserCourse.course).selectinload(Course.category),  # type: ignore
                selectinload(UserCourse.course).selectinload(Course.sub_category),  # type: ignore
                selectinload(UserCourse.course).selectinload(Course.modules),  # type: ignore
            )
        )
        user_course = result.scalar_one_or_none()
        if user_course is not None:
            cache_service.set(USER_COURSE_BY_ID_WITH_COURSE_CACHE, user_course_id, user_course)
        return user_course

    async def get_by_user_and_course_with_details(
        self, user_id: int, course_id: int, *, use_cache: bool = True
    ) -> Optional[UserCourse]:
        """Get user course by user ID and course ID with course details eagerly loaded."""
        from sqlalchemy.orm import selectinload

        cache_key = (user_id, course_id)
        if use_cache:
            cached = cache_service.get(USER_COURSE_BY_USER_AND_COURSE_DETAILS_CACHE, cache_key)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(UserCourse)
            .where(UserCourse.user_id == user_id)
            .where(UserCourse.course_id == course_id)
            .options(
                selectinload(UserCourse.course).selectinload(Course.category),  # type: ignore
                selectinload(UserCourse.course).selectinload(Course.sub_category),  # type: ignore
                selectinload(UserCourse.course).selectinload(Course.modules),  # type: ignore
            )
        )
        user_course = result.scalar_one_or_none()
        if user_course is not None:
            cache_service.set(USER_COURSE_BY_USER_AND_COURSE_DETAILS_CACHE, cache_key, user_course)
        return user_course

    async def create(self, user_course: UserCourse) -> UserCourse:
        """Create a new user course record."""
        self.session.add(user_course)
        await self.session.flush()
        await self.session.refresh(user_course)

        # Invalidate caches
        self.invalidate_cache(user_course.id, user_course.user_id, user_course.course_id)

        return user_course

    async def update(self, user_course: UserCourse) -> UserCourse:
        """Update an existing user course record."""
        self.session.add(user_course)
        await self.session.flush()
        await self.session.refresh(user_course)

        # Invalidate caches
        self.invalidate_cache(user_course.id, user_course.user_id, user_course.course_id)

        return user_course

    async def delete(self, user_course: UserCourse) -> None:
        """Delete a user course record."""
        user_course_id = user_course.id
        user_id = user_course.user_id
        course_id = user_course.course_id

        await self.session.delete(user_course)
        await self.session.flush()

        # Invalidate caches
        self.invalidate_cache(user_course_id, user_id, course_id)

    @staticmethod
    def invalidate_cache(user_course_id: int, user_id: int, course_id: int) -> None:
        """Manually invalidate the user course caches."""
        cache_service.delete(USER_COURSE_BY_ID_CACHE, user_course_id)
        cache_service.delete(USER_COURSE_BY_ID_WITH_COURSE_CACHE, user_course_id)
        cache_service.delete(USER_COURSE_BY_USER_AND_COURSE_CACHE, (user_id, course_id))
        cache_service.delete(USER_COURSE_BY_USER_AND_COURSE_DETAILS_CACHE, (user_id, course_id))
        cache_service.clear(USER_COURSE_LIST_BY_USER_CACHE)
        cache_service.clear(USER_COURSE_LIST_BY_USER_WITH_COURSE_CACHE)


class CategoryRepository:
    """Repository for category database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(
        self, skip: int = 0, limit: int = 100, search: Optional[str] = None, *, use_cache: bool = True
    ) -> List["Category"]:
        """Get all categories."""
        cache_key = (skip, limit, search)
        if use_cache:
            cached = cache_service.get(CATEGORY_LIST_ALL_CACHE, cache_key)
            if cached is not None:
                return cached

        query = select(Category)
        if search:
            query = query.where(
                col(Category.name).contains(search) | col(Category.description).contains(search)
            )

        result = await self.session.execute(query.offset(skip).limit(limit))
        categories = list(result.scalars().all())
        cache_service.set(CATEGORY_LIST_ALL_CACHE, cache_key, categories)
        return categories

    async def get_by_id(self, category_id: int, *, use_cache: bool = True) -> Optional["Category"]:
        """Get category by ID."""
        if use_cache:
            cached = cache_service.get(CATEGORY_BY_ID_CACHE, category_id)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        if category is not None:
            cache_service.set(CATEGORY_BY_ID_CACHE, category_id, category)
        return category

    async def get_by_name(self, name: str, *, use_cache: bool = True) -> Optional["Category"]:
        """Get category by name."""
        if use_cache:
            cached = cache_service.get(CATEGORY_BY_NAME_CACHE, name)
            if cached is not None:
                return cached

        result = await self.session.execute(
            select(Category).where(Category.name == name)
        )
        category = result.scalar_one_or_none()
        if category is not None:
            cache_service.set(CATEGORY_BY_NAME_CACHE, name, category)
        return category

    async def create(self, category: "Category") -> "Category":
        """Create a new category."""
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)

        # Invalidate caches
        self.invalidate_cache(category.id, category.name)

        return category

    async def update(self, category: "Category") -> "Category":
        """Update an existing category."""
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)

        # Invalidate caches
        self.invalidate_cache(category.id, category.name)

        return category

    async def delete(self, category: "Category") -> None:
        """Delete a category."""
        category_id = category.id
        category_name = category.name

        await self.session.delete(category)
        await self.session.flush()

        # Invalidate caches
        self.invalidate_cache(category_id, category_name)

    @staticmethod
    def invalidate_cache(category_id: int, category_name: str) -> None:
        """Manually invalidate the category caches."""
        cache_service.delete(CATEGORY_BY_ID_CACHE, category_id)
        cache_service.delete(CATEGORY_BY_NAME_CACHE, category_name)
        cache_service.clear(CATEGORY_LIST_ALL_CACHE)


class SubCategoryRepository:
    """Repository for sub-category database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, skip: int = 0, limit: int = 100) -> List["SubCategory"]:
        """Get all sub-categories."""
        result = await self.session.execute(
            select(SubCategory).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, sub_category_id: int) -> Optional["SubCategory"]:
        """Get sub-category by ID."""
        result = await self.session.execute(
            select(SubCategory).where(SubCategory.id == sub_category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_category_id(
        self, category_id: int, skip: int = 0, limit: int = 100
    ) -> List["SubCategory"]:
        """Get sub-categories by category ID."""
        result = await self.session.execute(
            select(SubCategory)
            .where(SubCategory.category_id == category_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Optional["SubCategory"]:
        """Get sub-category by name."""
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
