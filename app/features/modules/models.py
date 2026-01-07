"""Module database models."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel
from app.features.courses.models import ProgressStatus


class Module(SQLModel, table=True):
    """Module model for database."""
    
    __tablename__ = "modules"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="courses.id", nullable=False, index=True)
    title: str = Field(nullable=False)
    module_slug: str = Field(nullable=False, index=True)
    description: Optional[str] = Field(default=None)
    objectives: Optional[str] = Field(default=None)  # JSON string of objectives list
    order: int = Field(default=0, nullable=False)  # Order within the course
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    
    class Config:
        """Pydantic config."""
        from_attributes = True


class UserModule(SQLModel, table=True):
    """User Module junction table."""
    
    __tablename__ = "user_modules"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    course_id: int = Field(foreign_key="courses.id", nullable=False, index=True)
    module_id: int = Field(foreign_key="modules.id", nullable=False, index=True)
    status: ProgressStatus = Field(default=ProgressStatus.IN_PROGRESS)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    
    class Config:
        """Pydantic config."""
        from_attributes = True
