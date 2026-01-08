"""Module request/response schemas."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.features.courses.models import ProgressStatus


class ModuleBase(BaseModel):
    """Base module schema with common fields."""

    title: str
    module_slug: str
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    order: int = 0


class ModuleCreate(ModuleBase):
    """Schema for creating a new module."""

    course_id: int


class ModuleUpdate(BaseModel):
    """Schema for updating a module."""

    title: Optional[str] = None
    module_slug: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    order: Optional[int] = None


class ModuleResponse(ModuleBase):
    """Schema for module responses."""

    id: int
    course_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedModulesResponse(BaseModel):
    """Paginated modules response."""

    modules: List[ModuleResponse]
    page: int
    per_page: int
    total: int


# UserModule Schemas


class UserModuleBase(BaseModel):
    """Base user module schema."""

    status: ProgressStatus = ProgressStatus.IN_PROGRESS


class UserModuleCreate(BaseModel):
    """Schema for creating a user module record."""

    module_id: int
    course_id: int
    status: ProgressStatus = ProgressStatus.IN_PROGRESS


class UserModuleUpdate(BaseModel):
    """Schema for updating a user module record."""

    status: Optional[ProgressStatus] = None


class UserModuleResponse(BaseModel):
    """Schema for user module responses."""

    id: int
    user_id: int
    course_id: int
    module_id: int
    status: ProgressStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedUserModulesResponse(BaseModel):
    """Paginated user modules response."""

    user_modules: List[UserModuleResponse]
    page: int
    per_page: int
    total: int
