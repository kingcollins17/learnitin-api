"""Lesson database models."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column, Relationship
from typing import TYPE_CHECKING, Optional


from app.features.modules.models import Module
from app.features.quiz.models import Quiz

from sqlalchemy import Text, UniqueConstraint, ForeignKey, Integer
from sqlalchemy.dialects.mysql import LONGTEXT
from app.features.courses.models import ProgressStatus


class Lesson(SQLModel, table=True):
    """Lesson model for database."""

    __tablename__ = "lessons"

    id: Optional[int] = Field(default=None, primary_key=True)
    module_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("modules.id", ondelete="CASCADE"),
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
    title: str = Field(nullable=False)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    objectives: Optional[str] = Field(
        default=None, sa_column=Column(Text)
    )  # JSON string of objectives list
    content: Optional[str] = Field(
        default=None, sa_column=Column(LONGTEXT)
    )  # Markdown content (long text)
    audios: list["LessonAudio"] = Relationship(
        back_populates="lesson",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    order: int = Field(default=0, nullable=False)  # Order within the module
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)

    module: "Module" = Relationship(back_populates="lessons")
    quiz: Optional["Quiz"] = Relationship(
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
        back_populates="lesson",
    )

    class Config:
        """Pydantic config."""

        from_attributes = True


class LessonAudio(SQLModel, table=True):
    """Lesson Audio model for database."""

    __tablename__ = "lesson_audios"

    id: Optional[int] = Field(default=None, primary_key=True)
    lesson_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    title: str = Field(nullable=False)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    script: Optional[str] = Field(default=None, sa_column=Column(LONGTEXT))
    audio_url: Optional[str] = Field(default=None, sa_column=Column(Text))
    order: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)

    lesson: Optional["Lesson"] = Relationship(back_populates="audios")

    class Config:
        """Pydantic config."""

        from_attributes = True


class UserLesson(SQLModel, table=True):
    """User Lesson junction table."""

    __tablename__ = "user_lessons"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="unique_user_lesson"),
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
    module_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("modules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    lesson_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    is_lesson_unlocked: bool = Field(default=False)
    is_audio_unlocked: bool = Field(default=False)
    is_quiz_completed: bool = Field(default=False)
    status: ProgressStatus = Field(default=ProgressStatus.IN_PROGRESS)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)

    class Config:
        """Pydantic config."""

        from_attributes = True
