from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
from enum import Enum
from bubus import BaseEvent


class InAppEventType(str, Enum):
    """Types of in-app events for real-time notifications."""

    INFO = "info"
    AUDIO_READY = "audio_ready"
    AUDIO_GENERATION_FAILED = "audio_generation_failed"
    COURSE_ENROLLED = "course_enrolled"
    LESSON_COMPLETED = "lesson_completed"
    STREAK_UPDATED = "streak_updated"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"


class AppEvent(BaseEvent):
    """Base Event schema inheriting from bubus.BaseEvent."""

    pass


# --- Auth Events ---


class AuthRegisteredEvent(AppEvent):
    user_id: int
    email: str


class AuthLoginEvent(AppEvent):
    user_id: int
    email: str


class AuthPasswordResetRequestedEvent(AppEvent):
    user_id: int
    email: str
    token: str


class AuthEmailVerifiedEvent(AppEvent):
    user_id: int
    email: str


# --- Course Events ---


class CourseCreatedEvent(AppEvent):
    course_id: int
    title: str
    creator_id: int


class CourseUpdatedEvent(AppEvent):
    course_id: int
    updates: Dict[str, Any]


class CoursePublishedEvent(AppEvent):
    course_id: int


class CourseEnrolledEvent(AppEvent):
    user_id: int
    course_id: int


class CourseCompletedEvent(AppEvent):
    user_id: int
    course_id: int


# --- Lesson Events ---


class LessonCreateEvent(AppEvent):
    lesson_id: int
    course_id: int


class LessonStartedEvent(AppEvent):
    user_id: int
    lesson_id: int


class LessonCompletedEvent(AppEvent):
    user_id: int
    lesson_id: int


class LessonContentGeneratedEvent(AppEvent):
    lesson_id: int
    content: str


# --- Audio Events ---


class AudioGenerationRequestedEvent(AppEvent):
    user_id: int
    lesson_id: int


class AudioGenerationStartedEvent(AppEvent):
    lesson_id: int


class AudioReadyEvent(AppEvent):
    user_id: int
    lesson_id: int
    title: str
    count: int


class AudioGenerationFailedEvent(AppEvent):
    user_id: int
    lesson_id: int
    error: str


# --- Notification Events ---


class NotificationInAppPushEvent(AppEvent):
    user_id: int
    notification_id: Optional[int] = None
    title: str
    message: str
    type: str
    in_app_event: Optional[InAppEventType] = None
    data: Optional[Dict[str, Any]] = None
    created_at: str
