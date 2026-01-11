"""Course request/response schemas."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.features.courses.models import LearningPace, CourseLevel, ProgressStatus


class LessonOverview(BaseModel):
    """Overview of a lesson within a module."""

    title: str = Field(description="Lesson title")
    objectives: List[str] = Field(description="Learning objectives for this lesson")
    duration: str = Field(
        description="Estimated duration (e.g., '30 minutes', '1 hour')"
    )
    credit_cost: int = Field(
        default=0, description="Credits required to unlock (0-10, 0 for free lessons)"
    )


class ModuleOverview(BaseModel):
    """Overview of a module within a course."""

    title: str = Field(description="Module title")
    description: str = Field(description="Module description")
    duration: str = Field(description="Estimated duration for the module")
    objectives: Optional[List[str]] = Field(
        default=None, description="Learning objectives for this module"
    )
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
    level: str = Field(
        description="Difficulty level (e.g., 'beginner', 'intermediate', 'advanced')",
        default="intermediate",
    )
    learning_pace: str = Field(
        description="Learning Pace eg(fast, balanced, thorough)", default="balanced"
    )
    duration_preference: Optional[str] = Field(
        default="4 weeks",
        description="Preferred course duration (e.g., '2 weeks', '30 hours')",
    )
    learning_goals: Optional[List[str]] = Field(
        default=None, description="Specific learning goals or topics to cover"
    )


class CourseGenerationResponse(BaseModel):
    """Response schema for generated courses."""

    courses: List[CourseOutline] = Field(
        description="List of generated course outlines"
    )

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    """Base category schema."""

    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""

    pass


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(CategoryBase):
    """Schema for category response."""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SubCategoryBase(BaseModel):
    """Base sub-category schema."""

    name: str
    description: Optional[str] = None
    category_id: int


class SubCategoryCreate(SubCategoryBase):
    """Schema for creating a sub-category."""

    pass


class SubCategoryUpdate(BaseModel):
    """Schema for updating a sub-category."""

    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None


class SubCategoryResponse(SubCategoryBase):
    """Schema for sub-category response."""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Database schemas
class CourseBase(BaseModel):
    """Base course schema with common fields."""

    title: str
    description: str
    duration: str
    image_url: Optional[str] = None
    is_public: bool = False
    category_id: Optional[int] = None
    sub_category_id: Optional[int] = None


class CourseCreate(CourseBase):
    """Schema for creating a new course."""

    user_id: int


class CourseUpdate(BaseModel):
    """Schema for updating a course."""

    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    duration: Optional[str] = None
    is_public: Optional[bool] = None
    category_id: Optional[int] = None
    sub_category_id: Optional[int] = None


class CourseResponse(CourseBase):
    """Schema for course responses."""

    id: int
    user_id: int
    level: CourseLevel = CourseLevel.BEGINNER
    learning_pace: LearningPace = LearningPace.BALANCED
    total_enrollees: int = 0

    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional["CategoryResponse"] = None
    sub_category: Optional["SubCategoryResponse"] = None

    class Config:
        from_attributes = True


class LessonResponse(BaseModel):
    """Schema for lesson response."""

    id: int
    title: str
    description: Optional[str] = None
    objectives: Optional[str] = None  # JSON string of objectives list
    credit_cost: int = 0
    order: int

    class Config:
        from_attributes = True


class ModuleResponse(BaseModel):
    """Schema for module response."""

    id: int
    title: str
    description: Optional[str] = None
    objectives: Optional[str] = None  # JSON string of objectives list
    order: int
    lessons: List[LessonResponse] = []

    class Config:
        from_attributes = True


class CourseDetailResponse(CourseResponse):
    """Schema for course detail response including modules."""

    modules: List[ModuleResponse] = []


class UserCourseResponse(BaseModel):
    """Schema for user course response."""

    id: int
    course_id: int
    user_id: int
    status: ProgressStatus
    completed_modules: int
    course: CourseResponse

    class Config:
        from_attributes = True


class PaginatedCoursesResponse(BaseModel):
    """Schema for paginated courses response."""

    courses: List[CourseResponse]
    page: int
    per_page: int
    total: int

    class Config:
        from_attributes = True


class PaginatedUserCoursesResponse(BaseModel):
    """Schema for paginated user courses response."""

    courses: List[UserCourseResponse]
    page: int
    per_page: int
    total: int

    class Config:
        from_attributes = True
