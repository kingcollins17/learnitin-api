"""Module business logic and service layer."""

from fastapi import HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.features.modules.repository import ModuleRepository, UserModuleRepository
from app.features.modules.models import Module, UserModule
from app.features.courses.models import ProgressStatus
from app.features.courses.repository import UserCourseRepository
from app.features.lessons.repository import LessonRepository, UserLessonRepository
from app.common.service import Commitable


class ModuleService(Commitable):
    """Service for module business logic."""

    def __init__(self, module_repository: ModuleRepository):
        self.repository = module_repository

    async def commit_all(self) -> None:
        """Commit all active sessions in the service's repositories."""
        await self.repository.session.commit()

    async def get_modules_by_course(
        self, course_id: int, page: int = 1, per_page: int = 100
    ) -> List[Module]:
        """
        Get all modules for a specific course.

        Args:
            course_id: ID of the course
            page: Page number (1-indexed)
            per_page: Number of items per page

        Returns:
            List of modules for the course
        """
        skip = (page - 1) * per_page
        return await self.repository.get_by_course_id(
            course_id=course_id, skip=skip, limit=per_page
        )

    async def get_module_by_id(self, module_id: int) -> Optional[Module]:
        """
        Get module by ID.

        Args:
            module_id: ID of the module

        Returns:
            Module if found, None otherwise
        """
        return await self.repository.get_by_id(module_id)

    async def create_module(self, module_data: dict) -> Module:
        """
        Create a new module.

        Args:
            module_data: Dictionary containing module data

        Returns:
            Created Module object
        """
        module = Module(**module_data)
        return await self.repository.create(module)

    async def update_module(self, module_id: int, module_update: dict) -> Module:
        """
        Update a module.

        Args:
            module_id: ID of the module to update
            module_update: Dictionary of fields to update

        Returns:
            Updated Module object

        Raises:
            HTTPException: If module not found
        """
        module = await self.repository.get_by_id(module_id)

        if not module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Module not found",
            )

        # Update only provided fields
        for field, value in module_update.items():
            if value is not None and hasattr(module, field):
                setattr(module, field, value)

        # Update timestamp
        module.updated_at = datetime.now(timezone.utc)

        return await self.repository.update(module)

    async def delete_module(self, module_id: int) -> None:
        """
        Delete a module.

        Args:
            module_id: ID of the module to delete

        Raises:
            HTTPException: If module not found
        """
        module = await self.repository.get_by_id(module_id)

        if not module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Module not found",
            )

        await self.repository.delete(module)


class UserModuleService(Commitable):
    """Service for user module business logic."""

    def __init__(
        self,
        user_module_repository: UserModuleRepository,
        module_repository: ModuleRepository,
        user_course_repository: UserCourseRepository,
        lesson_repository: LessonRepository,
        user_lesson_repository: UserLessonRepository,
    ):
        self.repository = user_module_repository
        self.module_repo = module_repository
        self.user_course_repo = user_course_repository
        self.lesson_repo = lesson_repository
        self.user_lesson_repo = user_lesson_repository

    async def commit_all(self) -> None:
        """Commit all active sessions in the service's repositories."""
        await self.repository.session.commit()
        await self.module_repo.session.commit()
        await self.user_course_repo.session.commit()
        await self.lesson_repo.session.commit()
        await self.user_lesson_repo.session.commit()

    async def check_and_complete_module(self, user_id: int, module_id: int) -> bool:
        """
        Check if all lessons in a module are completed and mark module as completed.

        Args:
            user_id: ID of the user
            module_id: ID of the module

        Returns:
            True if module is completed, False otherwise
        """
        lessons = await self.lesson_repo.get_by_module_id(module_id)
        if not lessons:
            # If a module has no lessons, we consider it completed if it exists
            return True

        user_lessons = await self.user_lesson_repo.get_by_user_and_module(
            user_id, module_id
        )

        completed_lesson_ids = {
            ul.lesson_id for ul in user_lessons if ul.status == ProgressStatus.COMPLETED
        }

        all_completed = all(l.id in completed_lesson_ids for l in lessons)

        if all_completed:
            user_module = await self.repository.get_by_user_and_module(
                user_id, module_id
            )
            if user_module and user_module.status != ProgressStatus.COMPLETED:
                user_module.status = ProgressStatus.COMPLETED
                user_module.updated_at = datetime.now(timezone.utc)
                await self.repository.update(user_module)

                # Increment completed_modules in UserCourse
                user_course = await self.user_course_repo.get_by_user_and_course(
                    user_id, user_module.course_id
                )
                if user_course:
                    user_course.completed_modules += 1

                    # Check if all modules in course are completed
                    all_course_modules = await self.module_repo.get_by_course_id(
                        user_module.course_id
                    )
                    if user_course.completed_modules >= len(all_course_modules):
                        user_course.status = ProgressStatus.COMPLETED

                    user_course.updated_at = datetime.now(timezone.utc)
                    await self.user_course_repo.update(user_course)
            return True

        return False

    async def start_module(
        self, user_id: int, module_id: int, course_id: int
    ) -> UserModule:
        """
        Start a module for a user (create user module record).

        Args:
            user_id: ID of the user
            module_id: ID of the module
            course_id: ID of the course

        Returns:
            Created UserModule object

        Raises:
            HTTPException: If user module already exists
        """
        # Check if already started
        existing = await self.repository.get_by_user_and_module(user_id, module_id)

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has already started this module",
            )

        # Check if previous module is completed
        current_module = await self.module_repo.get_by_id(module_id)
        if not current_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Module not found",
            )

        previous_module = await self.module_repo.get_previous_module(
            course_id=course_id, current_order=current_module.order
        )

        if previous_module:
            assert previous_module.id is not None
            user_previous_module = await self.repository.get_by_user_and_module(
                user_id=user_id, module_id=previous_module.id
            )

            # Check if previous module is completed. If not, try to auto-complete it by checking lessons.
            if (
                not user_previous_module
                or user_previous_module.status != ProgressStatus.COMPLETED
            ):
                is_actually_completed = await self.check_and_complete_module(
                    user_id, previous_module.id
                )
                if not is_actually_completed:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"You must complete the previous module '{previous_module.title}' before starting this one.",
                    )

        # Create user module record
        user_module = UserModule(
            user_id=user_id,
            module_id=module_id,
            course_id=course_id,
            status=ProgressStatus.IN_PROGRESS,
        )

        created_user_module = await self.repository.create(user_module)

        # Update UserCourse progress
        user_course = await self.user_course_repo.get_by_user_and_course(
            user_id, course_id
        )
        if user_course:
            user_course.current_module_id = module_id
            user_course.updated_at = datetime.now(timezone.utc)
            await self.user_course_repo.update(user_course)

        return created_user_module

    async def get_user_modules_by_course(
        self, user_id: int, course_id: int
    ) -> List[UserModule]:
        """
        Get all user modules for a specific course.

        Args:
            user_id: ID of the user
            course_id: ID of the course

        Returns:
            List of user modules for the course
        """
        return await self.repository.get_by_user_and_course(user_id, course_id)

    async def get_user_module(
        self, user_id: int, module_id: int
    ) -> Optional[UserModule]:
        """
        Get user module by module ID.

        Args:
            user_id: ID of the user
            module_id: ID of the module

        Returns:
            UserModule if found

        Raises:
            HTTPException: If user module not found
        """
        user_module = await self.repository.get_by_user_and_module(user_id, module_id)

        if not user_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User module not found",
            )

        return user_module

    async def update_user_module(
        self, user_id: int, module_id: int, update_data: dict
    ) -> UserModule:
        """
        Update user module progress.

        Args:
            user_id: ID of the user
            module_id: ID of the module
            update_data: Dictionary of fields to update

        Returns:
            Updated UserModule object

        Raises:
            HTTPException: If user module not found
        """
        user_module = await self.repository.get_by_user_and_module(user_id, module_id)

        if not user_module:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User module not found",
            )

        # Update only provided fields
        for field, value in update_data.items():
            if value is not None and hasattr(user_module, field):
                setattr(user_module, field, value)

        # Update timestamp
        user_module.updated_at = datetime.now(timezone.utc)

        return await self.repository.update(user_module)

    async def complete_module(self, user_id: int, module_id: int) -> UserModule:
        """
        Mark a module as completed for a user.

        Args:
            user_id: ID of the user
            module_id: ID of the module

        Returns:
            Updated UserModule object
        """
        return await self.update_user_module(
            user_id=user_id,
            module_id=module_id,
            update_data={"status": ProgressStatus.COMPLETED},
        )
