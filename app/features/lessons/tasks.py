import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.lessons.service import LessonService
from app.features.lessons.repository import LessonAudioRepository


async def generate_audio_background(lesson_id: int, session: AsyncSession):
    """
    Background task to generate audio for a lesson.
    """
    try:
        lesson_service = LessonService(session)
        audio_repo = LessonAudioRepository(session)

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
            return

        if not lesson.content:
            print(f"Lesson content is empty for {lesson_id}, cannot generate audio.")
            return

        print(f"Generating audio for lesson {lesson_id}...")
        created_audios = await lesson_service.generate_audio_from_content(lesson_id)
        print(
            f"Audio generation completed for lesson {lesson_id}: {len(created_audios)} parts created"
        )

    except Exception as e:
        traceback.print_exc()
        print(f"Failed to generate audio for lesson {lesson_id}: {str(e)}")
