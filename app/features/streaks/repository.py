"""Repository for managing streaks database operations."""

from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from .models import CourseDailyStreak, CourseProgressEvent


class StreakRepository:
    """Repository for managing course progress events and daily course streaks."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_progress_event(self, event: CourseProgressEvent) -> CourseProgressEvent:
        """Create a new progress event."""
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def upsert_daily_streak(
        self, user_id: int, course_id: int, streak_date: date
    ) -> CourseDailyStreak:
        """
        Upsert a daily course streak entry.
        If it doesn't exist, create it. If it does, increment the progress count.
        """
        query = select(CourseDailyStreak).where(
            col(CourseDailyStreak.user_id) == user_id,
            col(CourseDailyStreak.course_id) == course_id,
            col(CourseDailyStreak.streak_date) == streak_date,
        )
        result = await self.session.execute(query)
        streak = result.scalar_one_or_none()

        if not streak:
            streak = CourseDailyStreak(
                user_id=user_id,
                course_id=course_id,
                streak_date=streak_date,
                completed=True,
                progress_count=1,
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(streak)
        else:
            streak.progress_count += 1
            streak.completed = True

        await self.session.flush()
        await self.session.refresh(streak)
        return streak

    async def get_daily_streaks(
        self, user_id: int, course_id: int, start_date: date, end_date: date
    ) -> List[CourseDailyStreak]:
        """Fetch all daily streaks for a specific user and course in a date range."""
        query = select(CourseDailyStreak).where(
            col(CourseDailyStreak.user_id) == user_id,
            col(CourseDailyStreak.course_id) == course_id,
            col(CourseDailyStreak.streak_date) >= start_date,
            col(CourseDailyStreak.streak_date) <= end_date,
        ).order_by(col(CourseDailyStreak.streak_date).asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_daily_streaks_for_user(
        self, user_id: int, start_date: date
    ) -> List[CourseDailyStreak]:
        """Fetch all daily streaks for all courses of a user starting from a specific date."""
        query = select(CourseDailyStreak).where(
            col(CourseDailyStreak.user_id) == user_id,
            col(CourseDailyStreak.streak_date) >= start_date,
        ).order_by(col(CourseDailyStreak.streak_date).asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_streaks_for_user_course(
        self, user_id: int, course_id: int
    ) -> List[CourseDailyStreak]:
        """Fetch all completed daily streaks for a course to calculate history/longest streak."""
        query = select(CourseDailyStreak).where(
            col(CourseDailyStreak.user_id) == user_id,
            col(CourseDailyStreak.course_id) == course_id,
            col(CourseDailyStreak.completed) == True,
        ).order_by(col(CourseDailyStreak.streak_date).asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())
