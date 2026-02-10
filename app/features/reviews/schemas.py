"""Review request/response schemas."""

from pydantic import BaseModel, Field
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.features.users.schemas import UserResponse
    from app.features.courses.schemas import CourseResponse


class ReviewBase(BaseModel):
    """Base review schema."""

    rating: Optional[int] = Field(
        default=None, ge=1, le=5, description="Rating from 1 to 5"
    )
    comment: Optional[str] = Field(default=None, description="Review comment")
    course_id: Optional[int] = Field(
        default=None, description="Course ID being reviewed"
    )


class ReviewCreate(ReviewBase):
    """Schema for creating a review."""

    pass


class ReviewUpdate(BaseModel):
    """Schema for updating a review."""

    rating: Optional[int] = Field(
        default=None, ge=1, le=5, description="Rating from 1 to 5"
    )
    comment: Optional[str] = Field(default=None, description="Review comment")


class ReviewResponse(ReviewBase):
    """Schema for review response."""

    id: Optional[int] = None
    user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user: Optional["UserResponse"] = None
    course: Optional["CourseResponse"] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class ReviewSummary(BaseModel):
    """Schema for course review summary."""

    average_rating: Optional[float] = Field(
        default=0.0, description="Average rating of the course"
    )
    total_reviews: Optional[int] = Field(
        default=0, description="Total number of reviews for the course"
    )


# Rebuild models to resolve forward references
from app.features.users.schemas import UserResponse
from app.features.courses.schemas import CourseResponse

ReviewResponse.model_rebuild()
