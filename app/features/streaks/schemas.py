"""Schemas for the streaks feature."""

from datetime import date
from enum import Enum
from typing import List
from pydantic import BaseModel


class WeekActivityStatus(str, Enum):
    """Activity status for a single day."""

    COMPLETED = "completed"
    MISSED = "missed"
    TODAY_PENDING = "today_pending"


class WeekActivityDay(BaseModel):
    """Represents a single day's activity status in a week."""

    date: str
    status: WeekActivityStatus


class CourseStreakResponse(BaseModel):
    """Streak statistics for a specific course."""

    course_id: int
    course_name: str
    current_streak: int
    longest_streak: int
    week_activity: List[WeekActivityDay]

    class Config:
        """Pydantic config."""

        from_attributes = True


class DashboardStatsResponse(BaseModel):
    """Aggregated learning dashboard statistics."""

    total_courses: int
    active_courses: int
    completed_courses: int
    overall_progress: float

    class Config:
        """Pydantic config."""

        from_attributes = True
