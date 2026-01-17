from enum import Enum


class EventType(str, Enum):
    """Enumeration of all possible event types in the system."""

    # Auth Events
    AUTH_REGISTERED = "auth.registered"
    AUTH_LOGIN = "auth.login"
    AUTH_PASSWORD_RESET_REQUESTED = "auth.password_reset_requested"
    AUTH_EMAIL_VERIFIED = "auth.email_verified"

    # Course Events
    COURSE_CREATED = "course.created"
    COURSE_UPDATED = "course.updated"
    COURSE_PUBLISHED = "course.published"
    COURSE_ENROLLED = "course.enrolled"
    COURSE_COMPLETED = "course.completed"

    # Module Events
    MODULE_CREATED = "module.created"
    MODULE_STARTED = "module.started"
    MODULE_COMPLETED = "module.completed"

    # Lesson Events
    LESSON_CREATED = "lesson.created"
    LESSON_STARTED = "lesson.started"
    LESSON_COMPLETED = "lesson.completed"
    LESSON_CONTENT_GENERATED = "lesson.content_generated"

    # Audio Events
    AUDIO_GENERATION_REQUESTED = "audio.generation_requested"
    AUDIO_GENERATION_STARTED = "audio.generation_started"
    AUDIO_GENERATION_COMPLETED = "audio.generation_completed"
    AUDIO_GENERATION_FAILED = "audio.generation_failed"

    # Quiz Events
    QUIZ_STARTED = "quiz.started"
    QUIZ_COMPLETED = "quiz.completed"
    QUIZ_FAILED = "quiz.failed"

    # User Progress Events
    USER_STREAK_UPDATED = "user.streak_updated"
    USER_ACHIEVEMENT_UNLOCKED = "user.achievement_unlocked"

    # Notification Events
    NOTIFICATION_IN_APP_PUSH = (
        "notification.in_app_push"  # Real-time notification over WebSocket
    )
    SYSTEM_NOTIFICATION_SENT = "system.notification_sent"
    SYSTEM_ERROR_LOGGED = "system.error_logged"
