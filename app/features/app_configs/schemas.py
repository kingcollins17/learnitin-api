"""App Configurations Pydantic schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AppConfigBase(BaseModel):
    """Base schema for AppConfig."""

    key: str = Field(..., description="Unique settings key")
    value: str = Field(..., description="Configuration value")
    metadata_json: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata fields", alias="metadata"
    )

    class Config:
        """Pydantic config."""

        populate_by_name = True


class AppConfigCreate(AppConfigBase):
    """Schema for creating a new AppConfig."""

    pass


class AppConfigUpdate(BaseModel):
    """Schema for updating an existing AppConfig."""

    key: Optional[str] = Field(None, description="Unique settings key")
    value: Optional[str] = Field(None, description="Configuration value")
    metadata_json: Optional[Dict[str, Any]] = Field(
        None, description="Optional metadata fields", alias="metadata"
    )

    class Config:
        """Pydantic config."""

        populate_by_name = True


class AppConfigResponse(AppConfigBase):
    """Response schema for AppConfig."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic config."""

        from_attributes = True
        populate_by_name = True
