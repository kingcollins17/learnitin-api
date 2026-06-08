"""Service for managing streaks business logic."""

from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from app.common.service import Commitable
from app.common.config import settings
from app.common.events import event_bus, NotificationInAppPushEvent, InAppEventType
from app.features.courses.repository import CourseRepository, UserCourseRepository
from app.features.courses.models import ProgressStatus
from app.features.credits.service import CreditService
from app.features.credits.models import CreditTransactionType
from .models import CourseDailyStreak, CourseProgressEvent
from .repository import StreakRepository
from .schemas import CourseStreakResponse, DashboardStatsResponse, WeekActivityDay, WeekActivityStatus


class StreakService(Commitable):
    """Service for managing course streaks and user dashboard statistics."""

    def __init__(
        self,
        streak_repository: StreakRepository,
        user_course_repository: UserCourseRepository,
        course_repository: CourseRepository,
        credit_service: CreditService,
    ):
        self.streak_repo = streak_repository
        self.user_course_repo = user_course_repository
        self.course_repo = course_repository
        self.credit_service = credit_service

    async def commit_all(self) -> None:
        """Commit all active database sessions."""
        await self.streak_repo.session.commit()
        await self.user_course_repo.session.commit()
        await self.course_repo.session.commit()

    def _get_local_date(self, dt: datetime, tz_name: str) -> date:
        """Convert a UTC datetime to a date in the given timezone."""
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("UTC")
        return dt.astimezone(tz).date()

    async def log_progress_event(
        self,
        user_id: int,
        course_id: int,
        lesson_id: Optional[int],
        event_type: str,
        timezone_str: str = "UTC",
        progress_amount: float = 0.0,
    ) -> CourseProgressEvent:
        """Log a learning progress event and upsert the daily streak record."""
        now_utc = datetime.now(timezone.utc)
        local_today = self._get_local_date(now_utc, timezone_str)

        # 1. Log the progress event
        event = CourseProgressEvent(
            user_id=user_id,
            course_id=course_id,
            lesson_id=lesson_id,
            event_type=event_type,
            progress_amount=progress_amount,
            created_at=now_utc,
        )
        await self.streak_repo.create_progress_event(event)

        # 2. Upsert the daily streak marker
        await self.streak_repo.upsert_daily_streak(
            user_id=user_id, course_id=course_id, streak_date=local_today
        )

        # 3. Check for 7-day streak bonus
        stats = await self.calculate_streak_stats(user_id, course_id, "Course", timezone_str)
        if stats.current_streak > 0 and stats.current_streak % 7 == 0:
            idemp_key = f"streak_bonus_{user_id}_{course_id}_{local_today.isoformat()}"
            try:
                existing = await self.credit_service.repository.get(idempotency_key=idemp_key)
                if not existing:
                    await self.credit_service.add_credits(
                        user_id=user_id,
                        amount=settings.STREAK_7_DAY_BONUS,
                        transaction_type=CreditTransactionType.BONUS,
                        description=f"Completed {stats.current_streak}-day streak!",
                        idempotency_key=idemp_key
                    )
                    await self.credit_service.commit_all()

                    # Dispatch notification
                    await event_bus.dispatch(
                        NotificationInAppPushEvent(
                            user_id=user_id,
                            title="Streak Bonus!",
                            message=f"You earned {settings.STREAK_7_DAY_BONUS} credits for a {stats.current_streak}-day streak!",
                            type="streak_bonus",
                            in_app_event=InAppEventType.INFO,
                            data={"streak": stats.current_streak, "credits": settings.STREAK_7_DAY_BONUS}
                        )
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to grant streak bonus: {e}")

        return event

    async def calculate_streak_stats(
        self, user_id: int, course_id: int, course_name: str, timezone_str: str = "UTC"
    ) -> CourseStreakResponse:
        """
        Calculate current streak, longest streak, and 7-day activity guide for a course.
        """
        now_utc = datetime.now(timezone.utc)
        local_today = self._get_local_date(now_utc, timezone_str)

        # Query all completed streak days to calculate current and longest streaks
        history = await self.streak_repo.get_all_streaks_for_user_course(user_id, course_id)
        completed_dates = {h.streak_date for h in history if h.completed}

        # 1. Current streak calculation
        current_streak = 0
        yesterday = local_today - timedelta(days=1)

        # A streak is alive if completed today or yesterday
        start_date = None
        if local_today in completed_dates:
            start_date = local_today
        elif yesterday in completed_dates:
            start_date = yesterday

        if start_date:
            curr = start_date
            while curr in completed_dates:
                current_streak += 1
                curr -= timedelta(days=1)

        # 2. Longest streak calculation
        longest_streak = 0
        if completed_dates:
            sorted_dates = sorted(list(completed_dates))
            temp_streak = 1
            longest_streak = 1
            for i in range(1, len(sorted_dates)):
                if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
                    temp_streak += 1
                else:
                    temp_streak = 1
                longest_streak = max(longest_streak, temp_streak)

        # 3. Construct 7-day week activity (last 6 days + today)
        week_activity: List[WeekActivityDay] = []
        for i in range(6, -1, -1):
            day = local_today - timedelta(days=i)
            day_str = day.isoformat()

            if day in completed_dates:
                status = WeekActivityStatus.COMPLETED
            elif day == local_today:
                status = WeekActivityStatus.TODAY_PENDING
            else:
                status = WeekActivityStatus.MISSED

            week_activity.append(WeekActivityDay(date=day_str, status=status))

        return CourseStreakResponse(
            course_id=course_id,
            course_name=course_name,
            current_streak=current_streak,
            longest_streak=longest_streak,
            week_activity=week_activity,
        )

    async def get_dashboard_stats(
        self, user_id: int, timezone_str: str = "UTC"
    ) -> DashboardStatsResponse:
        """Gather aggregated dashboard stats for the user."""
        # 1. Get all enrolled user courses with course details
        user_courses = await self.user_course_repo.get_by_user_with_course(user_id=user_id, limit=100)
        total_courses = len(user_courses)

        # 2. Calculate completed courses
        completed_courses = sum(
            1 for uc in user_courses if uc.status == ProgressStatus.COMPLETED
        )

        # 3. Calculate active courses (progress events within the last 7 days)
        now_utc = datetime.now(timezone.utc)
        cutoff_date = self._get_local_date(now_utc - timedelta(days=7), timezone_str)

        all_streaks = await self.streak_repo.get_all_daily_streaks_for_user(user_id, cutoff_date)
        active_course_ids = {s.course_id for s in all_streaks if s.completed}
        active_courses = len(active_course_ids)

        # 4. Overall completion progress
        total_progress = 0.0
        for uc in user_courses:
            if uc.status == ProgressStatus.COMPLETED:
                total_progress += 100.0
            else:
                total_l = uc.total_lessons
                if total_l > 0:
                    percent = (uc.completed_lessons / total_l) * 100.0
                    total_progress += min(percent, 100.0)

        overall_progress = (total_progress / total_courses) if total_courses > 0 else 0.0

        return DashboardStatsResponse(
            total_courses=total_courses,
            active_courses=active_courses,
            completed_courses=completed_courses,
            overall_progress=round(overall_progress, 1),
        )
