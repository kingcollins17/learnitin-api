"""Quiz and Question database models."""

from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.features.lessons.models import Lesson


class Quiz(SQLModel, table=True):
    """Quiz model for database."""

    __tablename__ = "quizzes"

    id: Optional[int] = Field(default=None, primary_key=True)
    lesson_id: int = Field(
        foreign_key="lessons.id", nullable=False, index=True, unique=True
    )
    duration: Optional[int] = Field(default=None)  # Duration in seconds, nullable
    passing_score: float = Field(default=0.7)  # Passing score ratio (0.0 - 1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    questions: List["Question"] = Relationship(
        back_populates="quiz", cascade_delete=True
    )
    lesson: "Lesson" = Relationship(back_populates="quiz")

    class Config:
        """Pydantic config."""

        from_attributes = True


class Question(SQLModel, table=True):
    """Question model for database."""

    __tablename__ = "questions"

    id: Optional[int] = Field(default=None, primary_key=True)
    quiz_id: int = Field(foreign_key="quizzes.id", nullable=False, index=True)
    lesson_id: int = Field(foreign_key="lessons.id", nullable=False, index=True)
    question: str = Field(nullable=False)
    option_1: Optional[str] = Field(default=None)
    option_2: Optional[str] = Field(default=None)
    option_3: Optional[str] = Field(default=None)
    option_4: Optional[str] = Field(default=None)
    explanation: Optional[str] = Field(default=None)
    correct_option_index: int = Field(nullable=False)  # 1 to 4
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    quiz: Quiz = Relationship(back_populates="questions")

    class Config:
        """Pydantic config."""

        from_attributes = True
