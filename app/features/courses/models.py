"""Course database models."""

from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy import Text, UniqueConstraint, ForeignKey, Integer
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.features.modules.models import Module


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


class Category(SQLModel, table=True):
    """Category model for grouping courses."""

    __tablename__ = "categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, nullable=False)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    courses: List["Course"] = Relationship(back_populates="category")
    sub_categories: List["SubCategory"] = Relationship(back_populates="category")


class SubCategory(SQLModel, table=True):
    """SubCategory model for more granular grouping."""

    __tablename__ = "sub_categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="categories.id", nullable=False, index=True)
    name: str = Field(unique=True, index=True, nullable=False)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    category: Category = Relationship(back_populates="sub_categories")
    courses: List["Course"] = Relationship(back_populates="sub_category")


class Course(SQLModel, table=True):
    """Course model for database."""

    __tablename__ = "courses"

    id: Optional[int] = Field(default=None, primary_key=True)
    category_id: Optional[int] = Field(default=None, foreign_key="categories.id")
    sub_category_id: Optional[int] = Field(
        default=None, foreign_key="sub_categories.id"
    )
    user_id: Optional[int] = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        description="User ID of the creator",
    )
    title: str = Field(nullable=False)
    description: str = Field(sa_column=Column(Text, nullable=False))
    image_url: Optional[str] = Field(default=None)
    duration: str = Field(nullable=False)  # e.g., "4 weeks", "30 hours"
    is_public: bool = Field(default=False)  # Whether the course is publicly accessible
    learning_pace: LearningPace = Field(default=LearningPace.BALANCED)
    level: CourseLevel = Field(default=CourseLevel.BEGINNER)
    total_enrollees: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)

    modules: List["Module"] = Relationship(back_populates="course")
    category: Optional["Category"] = Relationship(back_populates="courses")
    sub_category: Optional["SubCategory"] = Relationship(back_populates="courses")

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
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="unique_user_course"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    course_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    current_module_id: Optional[int] = Field(default=None, nullable=True)
    current_lesson_id: Optional[int] = Field(default=None, nullable=True)
    completed_modules: int = Field(default=0)
    status: ProgressStatus = Field(default=ProgressStatus.IN_PROGRESS)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)

    # Relationship to Course
    course: Optional["Course"] = Relationship()

    @property
    def total_modules(self) -> int:
        """Get the total number of modules in the course."""
        if self.course and self.course.modules:
            return len(self.course.modules)
        return 0

    class Config:
        """Pydantic config."""

        from_attributes = True
