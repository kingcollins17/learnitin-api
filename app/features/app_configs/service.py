"""App Configurations service layer."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from app.common.service import Commitable
from app.features.app_configs.models import AppConfig
from app.features.app_configs.repository import AppConfigRepository


class AppConfigService(Commitable):
    """Service for AppConfig business logic."""

    def __init__(self, repository: AppConfigRepository):
        self.repository = repository

    async def commit_all(self) -> None:
        """Commit active database sessions in repository."""
        await self.repository.session.commit()

    async def create_config(self, config_data: dict) -> AppConfig:
        """Create a new configuration."""
        key = config_data.get("key")
        if not key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Configuration key is required",
            )

        # Check if configuration with same key already exists
        existing = await self.repository.get_by_key(key)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Configuration with key '{key}' already exists",
            )

        config = AppConfig(
            key=key,
            value=config_data.get("value"),
            metadata_json=config_data.get("metadata_json"),
        )
        return await self.repository.create(config)

    async def get_configs(self, page: int = 1, per_page: int = 100) -> List[AppConfig]:
        """Get all configurations."""
        skip = (page - 1) * per_page
        return await self.repository.get_all(skip=skip, limit=per_page)

    async def get_config_by_key(self, key: str) -> AppConfig:
        """Get configuration by key."""
        config = await self.repository.get_by_key(key)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration with key '{key}' not found",
            )
        return config

    async def update_config(self, config_id: int, update_data: dict) -> AppConfig:
        """Update an existing configuration."""
        config = await self.repository.get_by_id(config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found",
            )

        # Check if key is being updated to a duplicate key
        new_key = update_data.get("key")
        if new_key and new_key != config.key:
            existing = await self.repository.get_by_key(new_key)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Configuration with key '{new_key}' already exists",
                )
            config.key = new_key

        if "value" in update_data and update_data["value"] is not None:
            config.value = update_data["value"]

        if "metadata_json" in update_data:
            config.metadata_json = update_data["metadata_json"]

        config.updated_at = datetime.now(timezone.utc)
        return await self.repository.update(config)

    async def delete_config(self, config_id: int) -> None:
        """Delete a configuration."""
        config = await self.repository.get_by_id(config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found",
            )

        await self.repository.delete(config)
