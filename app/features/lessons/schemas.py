"""Lesson request/response schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class LessonBase(BaseModel):
    """Base lesson schema with common fields."""
    title: str
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    content: Optional[str] = None  # Markdown content
    audio_transcript_url: Optional[str] = None
    is_unlocked: bool = False
    credit_cost: int = 0
    order: int = 0


class LessonCreate(LessonBase):
    """Schema for creating a new lesson."""
    module_id: int
    course_id: int


class LessonUpdate(BaseModel):
    """Schema for updating a lesson."""
    title: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    content: Optional[str] = None  # Markdown content
    audio_transcript_url: Optional[str] = None
    is_unlocked: Optional[bool] = None
    credit_cost: Optional[int] = None
    order: Optional[int] = None


class LessonResponse(LessonBase):
    """Schema for lesson responses."""
    id: int
    module_id: int
    course_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
