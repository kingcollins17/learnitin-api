"""Module business logic and service layer."""

from fastapi import HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.features.modules.repository import ModuleRepository, UserModuleRepository
from app.features.modules.models import Module, UserModule
from app.features.courses.models import ProgressStatus
from app.features.courses.repository import UserCourseRepository


class ModuleService:
    """Service for module business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ModuleRepository(session)

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


class UserModuleService:
    """Service for user module business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserModuleRepository(session)
        self.module_repo = ModuleRepository(session)
        self.user_course_repo = UserCourseRepository(session)

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
            if (
                not user_previous_module
                or user_previous_module.status != ProgressStatus.COMPLETED
            ):
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
