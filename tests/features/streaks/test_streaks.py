"""Tests for the streaks feature."""

import pytest
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from app.features.streaks.models import CourseDailyStreak, CourseProgressEvent
from app.features.streaks.repository import StreakRepository
from app.features.streaks.service import StreakService
from app.features.courses.repository import CourseRepository, UserCourseRepository
from app.features.courses.models import Course, UserCourse, ProgressStatus


@pytest.mark.asyncio
async def test_streak_calculations(db_session: AsyncSession):
    """Test dynamic current and longest streak calculation logic."""
    streak_repo = StreakRepository(db_session)
    user_course_repo = UserCourseRepository(db_session)
    course_repo = CourseRepository(db_session)

    service = StreakService(streak_repo, user_course_repo, course_repo)

    # Create user and course in DB to satisfy foreign keys
    from app.features.users.models import User
    user = User(email="streaktest@example.com", username="streaktest", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()

    course = Course(title="Test Chemistry", description="Chemistry course", user_id=user.id, duration="4 weeks")
    db_session.add(course)
    await db_session.flush()

    user_id = user.id
    course_id = course.id
    course_name = course.title

    # Today is 2026-05-27 based on current time
    today = date(2026, 5, 27)

    # Scenario 1: User completed today, yesterday, and day before yesterday (streak of 3)
    streak_1 = CourseDailyStreak(
        user_id=user_id,
        course_id=course_id,
        streak_date=today,
        completed=True,
        progress_count=1,
        created_at=datetime.now(timezone.utc),
    )
    streak_2 = CourseDailyStreak(
        user_id=user_id,
        course_id=course_id,
        streak_date=today - timedelta(days=1),
        completed=True,
        progress_count=2,
        created_at=datetime.now(timezone.utc),
    )
    streak_3 = CourseDailyStreak(
        user_id=user_id,
        course_id=course_id,
        streak_date=today - timedelta(days=2),
        completed=True,
        progress_count=1,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add_all([streak_1, streak_2, streak_3])
    await db_session.flush()

    stats = await service.calculate_streak_stats(
        user_id=user_id, course_id=course_id, course_name=course_name, timezone_str="UTC"
    )

    # Since today, yesterday, yesterday-1 are completed, current_streak should be 3
    assert stats.current_streak == 3
    assert stats.longest_streak == 3

    # Add a gap: yesterday-3 is missed, but yesterday-4, yesterday-5 are completed (streak of 2)
    streak_4 = CourseDailyStreak(
        user_id=user_id,
        course_id=course_id,
        streak_date=today - timedelta(days=4),
        completed=True,
        progress_count=1,
        created_at=datetime.now(timezone.utc),
    )
    streak_5 = CourseDailyStreak(
        user_id=user_id,
        course_id=course_id,
        streak_date=today - timedelta(days=5),
        completed=True,
        progress_count=1,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add_all([streak_4, streak_5])
    await db_session.flush()

    stats_with_gap = await service.calculate_streak_stats(
        user_id=user_id, course_id=course_id, course_name=course_name, timezone_str="UTC"
    )

    # Current streak is still 3 because of the gap, but longest streak should still be 3
    assert stats_with_gap.current_streak == 3
    assert stats_with_gap.longest_streak == 3

    # Now let's try with a longer historical streak
    streak_6 = CourseDailyStreak(
        user_id=user_id,
        course_id=course_id,
        streak_date=today - timedelta(days=6),
        completed=True,
        progress_count=1,
        created_at=datetime.now(timezone.utc),
    )
    streak_7 = CourseDailyStreak(
        user_id=user_id,
        course_id=course_id,
        streak_date=today - timedelta(days=7),
        completed=True,
        progress_count=1,
        created_at=datetime.now(timezone.utc),
    )
    streak_8 = CourseDailyStreak(
        user_id=user_id,
        course_id=course_id,
        streak_date=today - timedelta(days=8),
        completed=True,
        progress_count=1,
        created_at=datetime.now(timezone.utc),
    )
    streak_9 = CourseDailyStreak(
        user_id=user_id,
        course_id=course_id,
        streak_date=today - timedelta(days=9),
        completed=True,
        progress_count=1,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add_all([streak_6, streak_7, streak_8, streak_9])
    await db_session.flush()

    stats_long_history = await service.calculate_streak_stats(
        user_id=user_id, course_id=course_id, course_name=course_name, timezone_str="UTC"
    )

    # Longest streak should be 6 (from days 4 to 9 consecutive)
    assert stats_long_history.longest_streak == 6
