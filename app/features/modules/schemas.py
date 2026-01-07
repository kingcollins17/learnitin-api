"""Module request/response schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


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
