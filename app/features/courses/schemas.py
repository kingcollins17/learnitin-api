"""Course request/response schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class LessonOverview(BaseModel):
    """Overview of a lesson within a module."""
    title: str = Field(description="Lesson title")
    objectives: List[str] = Field(description="Learning objectives for this lesson")
    duration: str = Field(description="Estimated duration (e.g., '30 minutes', '1 hour')")
    credit_cost: int = Field(default=0, description="Credits required to unlock (0-10, 0 for free lessons)")


class ModuleOverview(BaseModel):
    """Overview of a module within a course."""
    title: str = Field(description="Module title")
    description: str = Field(description="Module description")
    duration: str = Field(description="Estimated duration for the module")
    lessons: List[LessonOverview] = Field(description="List of lessons in this module")


class CourseOutline(BaseModel):
    """Complete course outline with modules and lessons."""
    title: str = Field(description="Course title")
    description: str = Field(description="Course description")
    duration: str = Field(description="Total estimated duration")
    outline: List[ModuleOverview] = Field(description="List of modules in the course")


class CourseGenerationRequest(BaseModel):
    """Request schema for generating courses."""
    topic: str = Field(description="The topic or subject to learn")
    level: str = Field(description="Difficulty level (e.g., 'beginner', 'intermediate', 'advanced')", default='intermediate')
    learning_pace: str=Field(description="Learning Pace eg(fast, balanced, thorough)", default='balanced')
    duration_preference: Optional[str] = Field(
        default="4 weeks",
        description="Preferred course duration (e.g., '2 weeks', '30 hours')"
    )
    learning_goals: Optional[List[str]] = Field(
        default=None,
        description="Specific learning goals or topics to cover"
    )


class CourseGenerationResponse(BaseModel):
    """Response schema for generated courses."""
    courses: List[CourseOutline] = Field(description="List of generated course outlines")
    
    class Config:
        from_attributes = True


# Database schemas
class CourseBase(BaseModel):
    """Base course schema with common fields."""
    title: str
    description: str
    duration: str
    is_public: bool = False


class CourseCreate(CourseBase):
    """Schema for creating a new course."""
    user_id: int


class CourseUpdate(BaseModel):
    """Schema for updating a course."""
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[str] = None
    is_public: Optional[bool] = None


class CourseResponse(CourseBase):
    """Schema for course responses."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
