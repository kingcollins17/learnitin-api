"""Course business logic and service layer."""

from fastapi import HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.courses.repository import CourseRepository
from app.features.courses.schemas import (
    CourseOutline,
    CourseResponse,
)
from app.features.courses.models import (
    Course,
    UserCourse,
    LearningPace,
    CourseLevel,
    Category,
    SubCategory,
)
from app.features.modules.models import Module
from app.features.lessons.models import Lesson
from app.features.modules.repository import ModuleRepository
from app.features.lessons.repository import LessonRepository
from app.features.courses.repository import (
    UserCourseRepository,
    CategoryRepository,
    SubCategoryRepository,
)
from app.common.events import event_bus, CourseEnrolledEvent
from app.features.subscriptions.models import Subscription, SubscriptionResourceType
from app.features.subscriptions.usage_service import SubscriptionUsageService
import json
import re
import uuid
from app.services.image_generation_service import image_generation_service
from app.services.storage_service import firebase_storage_service


class CourseService:
    """Service for course business logic."""

    def __init__(
        self,
        session: AsyncSession,
        course_repository: CourseRepository,
        module_repository: ModuleRepository,
        lesson_repository: LessonRepository,
        user_course_repository: UserCourseRepository,
    ):
        self.session = session
        self.repository = course_repository
        self.module_repository = module_repository
        self.lesson_repository = lesson_repository
        self.user_course_repository = user_course_repository

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
            level=course_data.level,
        )

        course = await self.repository.create(course)

        # Generate Course Image
        if course.id:
            await self.generate_course_image(course.id)

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
                    module_data.objectives if module_data.objectives else []
                ),
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
                    order=j,
                )
                await self.lesson_repository.create(lesson)

        return course

    async def generate_course_image(self, course_id: int) -> Optional[str]:
        """
        Generate, upload and update a course with an image.

        Args:
            course_id: ID of the course to update

        Returns:
            The generated image URL or None if failed
        """
        try:
            # Fetch course from database
            course = await self.repository.get_by_id(course_id)
            if not course:
                print(f"Course not found for image generation: {course_id}")
                return None

            # Create a descriptive prompt for the image
            prompt = f"Abstract, modern, high quality cover image for an online course titled '{course.title}'. Context: {course.description[:200] if course.description else ''}"
            print(f"Generating course image with prompt: {prompt}")

            image_bytes = await image_generation_service.generate_image(prompt)

            if image_bytes:
                filename = f"courses/{course.user_id}/{uuid.uuid4()}.png"
                # Upload to firebase
                image_url = firebase_storage_service.upload_bytes(
                    data=image_bytes,
                    destination_path=filename,
                    content_type="image/png",
                )
                course.image_url = image_url

                # Update the course in the database
                await self.repository.update(course)

                print(f"Course image generated and uploaded to: {image_url}")
                return image_url
        except Exception as e:
            print(f"Failed to generate course image: {e}")

        return None

    async def enroll_course(
        self,
        user_id: int,
        course_id: int,
        usage_service: Optional[SubscriptionUsageService] = None,
        subscription: Optional[Subscription] = None,
    ) -> UserCourse:
        """
        Enroll a user in a course.

        Args:
            user_id: ID of the user to enroll
            course_id: ID of the course to enroll in
            usage_service: Optional service to increment usage
            subscription: Optional subscription to track usage for

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

        # Increment usage if service and subscription are provided
        if usage_service and subscription:
            await usage_service.increment_usage(
                subscription, SubscriptionResourceType.JOURNEY
            )

        # Emit course enrolled event
        event_bus.dispatch(CourseEnrolledEvent(user_id=user_id, course_id=course_id))

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
        category_id: Optional[int] = None,
        sub_category_id: Optional[int] = None,
        min_enrollees: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Course]:
        """
        Get all courses with pagination and filters.

        Args:
            page: Page number (1-indexed)
            per_page: Number of items per page
            is_public: Filter by public/private courses
            level: Filter by course level
            category_id: Filter by category ID
            sub_category_id: Filter by sub-category ID
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
            category_id=category_id,
            sub_category_id=sub_category_id,
            min_enrollees=min_enrollees,
            search=search,
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
        self,
        user_id: int,
        page: int = 1,
        per_page: int = 10,
        search: Optional[str] = None,
        level: Optional[str] = None,
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
            user_id=user_id, skip=skip, limit=per_page, search=search, level=level
        )

    async def get_user_course_detail(
        self, user_id: int, course_id: int
    ) -> Optional[UserCourse]:
        """
        Get user course detail.

        Args:
            user_id: ID of the user
            course_id: ID of the course

        Returns:
            UserCourse with course details, or None if not found

        Raises:
            HTTPException: If user course not found or doesn't belong to user
        """
        user_course = (
            await self.user_course_repository.get_by_user_and_course_with_details(
                user_id=user_id, course_id=course_id
            )
        )

        if not user_course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User course not found",
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

    async def unpublish_course(self, user_id: int, course_id: int) -> Course:
        """
        Unpublish a course.

        Args:
            user_id: ID of the user attempting to unpublish
            course_id: ID of the course to unpublish

        Returns:
            Updated Course object

        Raises:
            HTTPException: If course not found, user is not the creator, or course has more than 1 enrollee
        """
        course = await self.repository.get_by_id(course_id)

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Only the course creator can unpublish it
        if course.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to unpublish this course",
            )

        # Check if the course can be unpublished
        if course.total_enrollees > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This course cannot be unpublished because other users have enrolled in it.",
            )

        # Update is_public to False
        course.is_public = False

        # Update timestamp
        from datetime import datetime, timezone

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


class CategoryService:
    """Service for category business logic."""

    def __init__(self, session: AsyncSession, category_repository: CategoryRepository):
        self.session = session
        self.category_repository = category_repository

    async def create_category(self, category_data: dict) -> Category:
        """Create a new category."""
        # Check if category with same name exists
        existing_category = await self.category_repository.get_by_name(
            category_data["name"]
        )
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists",
            )

        category = Category(**category_data)
        return await self.category_repository.create(category)

    async def get_categories(
        self, page: int = 1, per_page: int = 100
    ) -> List[Category]:
        """Get all categories."""
        skip = (page - 1) * per_page
        return await self.category_repository.get_all(skip=skip, limit=per_page)

    async def update_category(
        self, category_id: int, category_update: dict
    ) -> Category:
        """Update a category."""
        category = await self.category_repository.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        # Update fields
        for field, value in category_update.items():
            if value is not None:
                setattr(category, field, value)

        return await self.category_repository.update(category)

    async def delete_category(self, category_id: int) -> None:
        """Delete a category."""
        category = await self.category_repository.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        await self.category_repository.delete(category)


class SubCategoryService:
    """Service for sub-category business logic."""

    def __init__(
        self,
        session: AsyncSession,
        subcategory_repository: SubCategoryRepository,
        category_repository: CategoryRepository,
    ):
        self.session = session
        self.subcategory_repository = subcategory_repository
        self.category_repository = category_repository

    async def create_subcategory(self, sub_category_data: dict) -> SubCategory:
        """Create a new sub-category."""
        # Check if category exists
        category = await self.category_repository.get_by_id(
            sub_category_data["category_id"]
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        # Check if sub-category with same name exists
        existing_subcategory = await self.subcategory_repository.get_by_name(
            sub_category_data["name"]
        )
        if existing_subcategory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sub-category with this name already exists",
            )

        sub_category = SubCategory(**sub_category_data)
        return await self.subcategory_repository.create(sub_category)

    async def get_subcategories(
        self, page: int = 1, per_page: int = 100, category_id: Optional[int] = None
    ) -> List[SubCategory]:
        """Get all sub-categories, optionally filtered by category."""
        skip = (page - 1) * per_page
        if category_id:
            return await self.subcategory_repository.get_by_category_id(
                category_id=category_id, skip=skip, limit=per_page
            )
        return await self.subcategory_repository.get_all(skip=skip, limit=per_page)

    async def update_subcategory(
        self, sub_category_id: int, sub_category_update: dict
    ) -> SubCategory:
        """Update a sub-category."""
        sub_category = await self.subcategory_repository.get_by_id(sub_category_id)
        if not sub_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sub-category not found",
            )

        # If updating category_id, check if new category exists
        if (
            "category_id" in sub_category_update
            and sub_category_update["category_id"] is not None
        ):
            category = await self.category_repository.get_by_id(
                sub_category_update["category_id"]
            )
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found",
                )

        # Update fields
        for field, value in sub_category_update.items():
            if value is not None:
                setattr(sub_category, field, value)

        return await self.subcategory_repository.update(sub_category)

    async def delete_subcategory(self, sub_category_id: int) -> None:
        """Delete a sub-category."""
        sub_category = await self.subcategory_repository.get_by_id(sub_category_id)
        if not sub_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sub-category not found",
            )

        await self.subcategory_repository.delete(sub_category)
