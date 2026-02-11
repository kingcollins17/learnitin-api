import traceback
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.lessons.service import LessonService
from app.features.lessons.repository import LessonAudioRepository
from datetime import datetime, timezone
from app.common.events import (
    event_bus,
    AudioReadyEvent,
    AudioGenerationFailedEvent,
    NotificationInAppPushEvent,
    InAppEventType,
)


from app.features.lessons.lesson_audio_tracker import audio_tracker
from app.features.lessons.lesson_content_tracker import content_tracker
from app.features.notifications.service import NotificationService
from app.features.notifications.schemas import NotificationCreate
from app.features.notifications.models import NotificationType
from app.features.courses.repository import CourseRepository
from app.features.modules.repository import ModuleRepository


async def generate_audio_background(
    lesson_id: int,
    lesson_service: LessonService,
    user_id: Optional[int] = None,
):
    """
    Background task to generate audio for a lesson.
    """
    try:
        audio_repo = lesson_service.audio_repo

        # 1. Get the lesson
        lesson = await lesson_service.get_lesson_by_id(lesson_id)
        if not lesson:
            print(f"Lesson {lesson_id} not found during background audio generation.")
            return

        # Check if audio parts already exist
        existing_audios = await audio_repo.get_by_lesson_id(lesson_id)
        if existing_audios:
            print(
                f"Audio parts already exist for lesson {lesson_id} ({len(existing_audios)} parts)."
            )
            # Still publish completed if user is waiting
            if user_id:
                event_bus.dispatch(
                    AudioReadyEvent(
                        user_id=user_id,
                        lesson_id=lesson_id,
                        title=lesson.title,
                        count=len(existing_audios),
                    )
                )
                # Dispatch transient notification
                event_bus.dispatch(
                    NotificationInAppPushEvent(
                        user_id=user_id,
                        title="Audio Ready",
                        message=f"Audio for '{lesson.title}' is ready to listen.",
                        type="success",
                        in_app_event=InAppEventType.AUDIO_READY,
                        data={"lesson_id": lesson_id},
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                )
            return

        if not lesson.content:
            print(f"Lesson content is empty for {lesson_id}, cannot generate audio.")
            return

        print(f"Generating audio for lesson {lesson_id}...")
        created_audios = await lesson_service.generate_audio_from_content(lesson_id)

        print(
            f"Audio generation completed for lesson {lesson_id}: {len(created_audios)} parts created"
        )

        # Publish completion events
        if user_id:
            # 1. Dispatch AudioReadyEvent
            event_bus.dispatch(
                AudioReadyEvent(
                    user_id=user_id,
                    lesson_id=lesson_id,
                    title=lesson.title,
                    count=len(created_audios),
                )
            )
            # 2. Dispatch transient notification (WS only, not in DB)
            event_bus.dispatch(
                NotificationInAppPushEvent(
                    user_id=user_id,
                    title="Audio Ready",
                    message=f"Audio for '{lesson.title}' is now ready to listen.",
                    type="success",
                    in_app_event=InAppEventType.AUDIO_READY,
                    data={"lesson_id": lesson_id},
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )

    except Exception as e:
        traceback.print_exc()
        error_msg = f"Failed to generate audio for lesson {lesson_id}: {str(e)}"
        print(error_msg)

        # Publish failure event
        if user_id:
            event_bus.dispatch(
                AudioGenerationFailedEvent(
                    user_id=user_id,
                    lesson_id=lesson_id,
                    error=str(e),
                )
            )
    finally:
        # Stop tracking so new generation can be requested if needed
        audio_tracker.stop_tracking(lesson_id)


async def generate_lesson_content_background(
    lesson_id: int,
    lesson_service: LessonService,
    notification_service: NotificationService,
    user_id: int,
    course_id: int,
    module_id: int,
):
    """
    Background task to generate lesson content.
    """
    try:
        # 1. Get the lesson
        lesson = await lesson_service.get_lesson_by_id(lesson_id)
        if not lesson:
            print(f"Lesson {lesson_id} not found during background content generation.")
            return

        # Check if content already exists
        if lesson.content:
            print(f"Content already exists for lesson {lesson_id}.")
            return

        # Fetch course and module details for context
        course_repo = lesson_service.course_repo
        module_repo = lesson_service.module_repo

        course = await course_repo.get_by_id(course_id)
        module = await module_repo.get_by_id(module_id)

        if not course or not module:
            print(f"Course or Module not found for lesson {lesson_id}.")
            return

        print(f"Generating content for lesson {lesson_id}...")
        generated_content = (
            await lesson_service.generation_service.generate_lesson_content(
                course=course,
                module=module,
                lesson=lesson,
            )
        )

        # Update lesson with generated content
        await lesson_service.update_lesson(
            lesson_id=lesson_id,
            lesson_update={"content": generated_content},
        )
        await lesson_service.repository.session.commit()
        print(f"Content generated and saved for lesson {lesson_id}")

        # Dispatch in-app notification
        await notification_service.create_notification(
            notification_data=NotificationCreate(
                user_id=user_id,
                title="Lesson Ready",
                message=f"The content for '{lesson.title}' is now ready.",
                type=NotificationType.INFO,
                data={
                    "lesson_id": lesson_id,
                    "in_app_event": InAppEventType.LESSON_READY,
                },
            )
        )

    except Exception as e:
        traceback.print_exc()
        print(f"Failed to generate content for lesson {lesson_id}: {str(e)}")
    finally:
        # Stop tracking
        content_tracker.stop_tracking(lesson_id)
