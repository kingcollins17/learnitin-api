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
    SUBSCRIPTION_PURCHASED = "subscription_purchased"


class AppEvent(BaseEvent):
    """Base Event schema inheriting from bubus.BaseEvent."""

    pass


# --- Auth Events ---


class AuthRegisteredEvent(AppEvent):
    user_id: Optional[int] = None
    email: Optional[str] = None


class AuthLoginEvent(AppEvent):
    user_id: Optional[int] = None
    email: Optional[str] = None


class AuthPasswordResetRequestedEvent(AppEvent):
    user_id: Optional[int] = None
    email: Optional[str] = None
    token: Optional[str] = None


class AuthEmailVerifiedEvent(AppEvent):
    user_id: Optional[int] = None
    email: Optional[str] = None


# --- Course Events ---


class CourseCreatedEvent(AppEvent):
    course_id: Optional[int] = None
    title: Optional[str] = None
    creator_id: Optional[int] = None


class CourseUpdatedEvent(AppEvent):
    course_id: Optional[int] = None
    updates: Optional[Dict[str, Any]] = None


class CoursePublishedEvent(AppEvent):
    course_id: Optional[int] = None


class CourseEnrolledEvent(AppEvent):
    user_id: Optional[int] = None
    course_id: Optional[int] = None


class CourseCompletedEvent(AppEvent):
    user_id: Optional[int] = None
    course_id: Optional[int] = None


# --- Lesson Events ---


class LessonCreateEvent(AppEvent):
    lesson_id: Optional[int] = None
    course_id: Optional[int] = None


class LessonStartedEvent(AppEvent):
    user_id: Optional[int] = None
    lesson_id: Optional[int] = None


class LessonCompletedEvent(AppEvent):
    user_id: Optional[int] = None
    lesson_id: Optional[int] = None


class LessonContentGeneratedEvent(AppEvent):
    lesson_id: Optional[int] = None
    content: Optional[str] = None


# --- Quiz Events ---


class QuizGeneratedEvent(AppEvent):
    quiz_id: Optional[int] = None
    lesson_id: Optional[int] = None
    question_count: Optional[int] = None


# --- Audio Events ---


class AudioGenerationRequestedEvent(AppEvent):
    user_id: Optional[int] = None
    lesson_id: Optional[int] = None


class AudioGenerationStartedEvent(AppEvent):
    lesson_id: Optional[int] = None


class AudioReadyEvent(AppEvent):
    user_id: Optional[int] = None
    lesson_id: Optional[int] = None
    title: Optional[str] = None
    count: Optional[int] = None


class AudioGenerationFailedEvent(AppEvent):
    user_id: Optional[int] = None
    lesson_id: Optional[int] = None
    error: Optional[str] = None


# --- Notification Events ---


class NotificationInAppPushEvent(AppEvent):
    user_id: Optional[int] = None
    notification_id: Optional[int] = None
    title: Optional[str] = None
    message: Optional[str] = None
    type: Optional[str] = None
    in_app_event: Optional[InAppEventType] = None
    data: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
