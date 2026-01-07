"""Module repository for database operations."""
from typing import Optional, List
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.features.modules.models import Module, UserModule


class ModuleRepository:
    """Repository for module database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, module_id: int) -> Optional[Module]:
        """Get module by ID."""
        result = await self.session.execute(
            select(Module).where(Module.id == module_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_course_id(self, course_id: int, skip: int = 0, limit: int = 100) -> List[Module]:
        """Get all modules for a specific course."""
        result = await self.session.execute(
            select(Module)
            .where(Module.course_id == course_id)
            .order_by(Module.order)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_slug(self, module_slug: str, course_id: int) -> Optional[Module]:
        """Get module by slug within a course."""
        result = await self.session.execute(
            select(Module)
            .where(Module.module_slug == module_slug)
            .where(Module.course_id == course_id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, module: Module) -> Module:
        """Create a new module."""
        self.session.add(module)
        await self.session.flush()
        await self.session.refresh(module)
        return module
    
    async def update(self, module: Module) -> Module:
        """Update an existing module."""
        self.session.add(module)
        await self.session.flush()
        await self.session.refresh(module)
        return module
    
    async def delete(self, module: Module) -> None:
        """Delete a module."""
        await self.session.delete(module)
        await self.session.flush()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Module]:
        """Get all modules with pagination."""
        result = await self.session.execute(
            select(Module).order_by(Module.course_id, Module.order).offset(skip).limit(limit)
        )
        return list(result.scalars().all())


class UserModuleRepository:
    """Repository for user module database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, user_module_id: int) -> Optional[UserModule]:
        """Get user module by ID."""
        result = await self.session.execute(
            select(UserModule).where(UserModule.id == user_module_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_user_and_module(self, user_id: int, module_id: int) -> Optional[UserModule]:
        """Get user module by user ID and module ID."""
        result = await self.session.execute(
            select(UserModule)
            .where(UserModule.user_id == user_id)
            .where(UserModule.module_id == module_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_user_and_course(self, user_id: int, course_id: int) -> List[UserModule]:
        """Get all user modules for a specific course."""
        result = await self.session.execute(
            select(UserModule)
            .where(UserModule.user_id == user_id)
            .where(UserModule.course_id == course_id)
        )
        return list(result.scalars().all())
    
    async def create(self, user_module: UserModule) -> UserModule:
        """Create a new user module record."""
        self.session.add(user_module)
        await self.session.flush()
        await self.session.refresh(user_module)
        return user_module
    
    async def update(self, user_module: UserModule) -> UserModule:
        """Update an existing user module record."""
        self.session.add(user_module)
        await self.session.flush()
        await self.session.refresh(user_module)
        return user_module
    
    async def delete(self, user_module: UserModule) -> None:
        """Delete a user module record."""
        await self.session.delete(user_module)
        await self.session.flush()
