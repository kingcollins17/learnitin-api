"""Lesson request/response schemas."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from app.features.courses.models import ProgressStatus


class LessonBase(BaseModel):
    """Base lesson schema with common fields."""

    title: str
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    # content is excluded from base to avoid sending it in lists
    audio_transcript_url: Optional[str] = None
    has_quiz: bool = False
    credit_cost: int = 0
    audio_credit_cost: int = 0
    order: int = 0


class LessonCreate(LessonBase):
    """Schema for creating a new lesson."""

    content: Optional[str] = None  # Markdown content
    module_id: int
    course_id: int


class LessonUpdate(BaseModel):
    """Schema for updating a lesson."""

    title: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    content: Optional[str] = None  # Markdown content
    audio_transcript_url: Optional[str] = None
    has_quiz: Optional[bool] = None
    credit_cost: Optional[int] = None
    audio_credit_cost: Optional[int] = None
    order: Optional[int] = None


class LessonResponse(LessonBase):
    """Schema for lesson responses (list view)."""

    id: int
    module_id: int
    course_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        # Handle SQLAlchemy model instance where objectives is a JSON string
        if hasattr(obj, "objectives") and isinstance(obj.objectives, str):
            import json

            try:
                # If it's a string, try to load it as JSON
                # Create a copy or a dictionary representation to modify
                if hasattr(obj, "__dict__"):
                    # We can't modify the SQLModel instance safely here usually,
                    # but Pydantic's from_attributes uses getattr.
                    # Instead, we should use a field validator or pre-validator.
                    pass
            except json.JSONDecodeError:
                pass
        return super().model_validate(obj, *args, **kwargs)

    @field_validator("objectives", mode="before")
    @classmethod
    def parse_objectives(cls, v):
        if isinstance(v, str):
            try:
                import json

                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v


class LessonDetailResponse(LessonResponse):
    """Schema for detailed lesson response including content."""

    content: Optional[str] = None  # Markdown content


class PaginatedLessonsResponse(BaseModel):
    """Paginated lessons response."""

    lessons: List[LessonResponse]
    page: int
    per_page: int
    total: int


# UserLesson Schemas


class UserLessonBase(BaseModel):
    """Base user lesson schema."""

    is_lesson_unlocked: bool = False
    is_audio_unlocked: bool = False
    is_quiz_completed: bool = False
    status: ProgressStatus = ProgressStatus.IN_PROGRESS


class LessonStartRequest(BaseModel):
    """Schema for starting a lesson."""

    lesson_id: int


class UserLessonCreate(BaseModel):
    """Schema for creating a user lesson record."""

    lesson_id: int
    module_id: int
    course_id: int
    is_lesson_unlocked: bool = False
    is_audio_unlocked: bool = False
    is_quiz_completed: bool = False
    status: ProgressStatus = ProgressStatus.IN_PROGRESS


class UserLessonUpdate(BaseModel):
    """Schema for updating a user lesson record."""

    is_lesson_unlocked: Optional[bool] = None
    is_audio_unlocked: Optional[bool] = None
    is_quiz_completed: Optional[bool] = None
    status: Optional[ProgressStatus] = None


class UserLessonResponse(BaseModel):
    """Schema for user lesson responses."""

    id: int
    user_id: int
    course_id: int
    module_id: int
    lesson_id: int
    is_lesson_unlocked: bool
    is_audio_unlocked: bool
    is_quiz_completed: bool
    status: ProgressStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    audio_transcript_url: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedUserLessonsResponse(BaseModel):
    """Paginated user lessons response."""

    user_lessons: List[UserLessonResponse]
    page: int
    per_page: int
    total: int
