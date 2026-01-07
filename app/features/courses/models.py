"""Course database models."""
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from enum import Enum
from sqlmodel import Field, SQLModel



class LearningPace(str, Enum):
    """Learning pace options."""
    
    FAST = "fast"
    BALANCED = "balanced"
    THOROUGH = "thorough"


class CourseLevel(str, Enum):
    """Course level options."""
    
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class Course(SQLModel, table=True):
    """Course model for database."""
    
    __tablename__ = "courses"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True, description="User ID of the creator")
    title: str = Field(nullable=False)
    description: str = Field(nullable=False)
    duration: str = Field(nullable=False)  # e.g., "4 weeks", "30 hours"
    is_public: bool = Field(default=False)  # Whether the course is publicly accessible
    learning_pace: LearningPace = Field(default=LearningPace.BALANCED)
    level: CourseLevel = Field(default=CourseLevel.BEGINNER)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    
    class Config:
        """Pydantic config."""
        from_attributes = True


class ProgressStatus(str, Enum):
    """Status of progress."""
    
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"




class UserCourse(SQLModel, table=True):
    """User Course junction table."""
    
    __tablename__ = "user_courses"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    course_id: int = Field(foreign_key="courses.id", nullable=False, index=True)
    current_lesson_id: Optional[int] = Field(default=None, foreign_key="lessons.id", index=True)
    completed_modules: int = Field(default=0)
    status: ProgressStatus = Field(default=ProgressStatus.IN_PROGRESS)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    
    class Config:
        """Pydantic config."""
        from_attributes = True
