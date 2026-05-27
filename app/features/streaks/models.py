"""Streak database models."""

from datetime import datetime, date, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import BigInteger, String, ForeignKey, UniqueConstraint, DateTime, Date, Boolean, Integer, Float


class CourseProgressEvent(SQLModel, table=True):
    """Course Progress Events table for logging learning events."""

    __tablename__ = "course_progress_events"

    id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    course_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    lesson_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("lessons.id", ondelete="SET NULL"),
            nullable=True,
        )
    )
    event_type: str = Field(
        sa_column=Column(String(50), nullable=False)
    )  # e.g. "lesson_started", "lesson_completed", "quiz_completed"
    progress_amount: float = Field(
        default=0.0,
        sa_column=Column(Float, default=0.0)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False, index=True)
    )

    class Config:
        """Pydantic config."""

        from_attributes = True


class CourseDailyStreak(SQLModel, table=True):
    """Aggregated daily course completion records for fast home feed rendering."""

    __tablename__ = "course_daily_streaks"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "course_id",
            "streak_date",
            name="uq_user_course_date"
        ),
    )

    id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    course_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    streak_date: date = Field(
        sa_column=Column(Date, nullable=False, index=True)
    )
    completed: bool = Field(
        default=False,
        sa_column=Column(Boolean, default=False)
    )
    progress_count: int = Field(
        default=0,
        sa_column=Column(Integer, default=0)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime, nullable=False)
    )

    class Config:
        """Pydantic config."""

        from_attributes = True
