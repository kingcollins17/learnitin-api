"""App Configurations database models."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import Field, SQLModel, Column, JSON


class AppConfig(SQLModel, table=True):
    """AppConfig model for database."""

    __tablename__ = "app_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True, nullable=False)
    value: str = Field(nullable=False)
    metadata_json: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column("metadata", JSON)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Optional[datetime] = Field(default=None)

    class Config:
        """Pydantic config."""

        from_attributes = True
