"""App Configurations repository for database operations."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col
from app.features.app_configs.models import AppConfig


class AppConfigRepository:
    """Repository for AppConfig database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[AppConfig]:
        """Get all configurations with pagination."""
        query = select(AppConfig).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, config_id: int) -> Optional[AppConfig]:
        """Get configuration by ID."""
        result = await self.session.execute(
            select(AppConfig).where(AppConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> Optional[AppConfig]:
        """Get configuration by unique key."""
        result = await self.session.execute(
            select(AppConfig).where(AppConfig.key == key)
        )
        return result.scalar_one_or_none()

    async def create(self, config: AppConfig) -> AppConfig:
        """Create a new configuration."""
        self.session.add(config)
        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def update(self, config: AppConfig) -> AppConfig:
        """Update an existing configuration."""
        self.session.add(config)
        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def delete(self, config: AppConfig) -> None:
        """Delete a configuration."""
        await self.session.delete(config)
        await self.session.flush()
