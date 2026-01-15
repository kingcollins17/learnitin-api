import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.lessons.service import LessonService


async def generate_audio_background(lesson_id: int, session: AsyncSession):
    """
    Background task to generate audio for a lesson.
    """
    try:
        lesson_service = LessonService(session)
        # 1. Get the lesson
        lesson = await lesson_service.get_lesson_by_id(lesson_id)
        if not lesson:
            print(f"Lesson {lesson_id} not found during background audio generation.")
            return

        if lesson.audio_transcript_url:
            print(f"Audio already exists for lesson {lesson_id}.")
            return

        if not lesson.content:
            print(f"Lesson content is empty for {lesson_id}, cannot generate audio.")
            return

        print(f"Generating audio for lesson {lesson_id}...")
        await lesson_service.generate_audio_from_content(lesson_id)
        print(f"Audio generation completed for lesson {lesson_id}")

    except Exception as e:
        traceback.print_exc()
        print(f"Failed to generate audio for lesson {lesson_id}: {str(e)}")
