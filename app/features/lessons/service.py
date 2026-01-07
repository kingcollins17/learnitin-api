"""Service for managing lessons."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.lessons.models import Lesson
from app.features.lessons.repository import LessonRepository
from app.features.lessons.generation_service import lesson_generation_service
from app.features.courses.repository import CourseRepository
from app.features.modules.repository import ModuleRepository

class LessonService:
    """Service for lesson business logic."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = LessonRepository(session)
        self.course_repo = CourseRepository(session)
        self.module_repo = ModuleRepository(session)
        self.generation_service = lesson_generation_service
        
    async def generate_content(self, lesson_id: int) -> Optional[Lesson]:
        """
        Generate content for a lesson and update it.
        
        Args:
            lesson_id: ID of the lesson to generate content for
            
        Returns:
            Updated lesson with generated content
        """
        lesson = await self.repository.get_by_id(lesson_id)
        if not lesson:
            return None
            
        course = await self.course_repo.get_by_id(lesson.course_id)
        module = await self.module_repo.get_by_id(lesson.module_id)
        
        if not course or not module:
            # Should not happen in consistent DB, but good to handle
            return None
            
        content = await self.generation_service.generate_lesson_content(
            course=course,
            module=module,
            lesson=lesson
        )
        
        lesson.content = content
        return await self.repository.update(lesson)
        
    async def generate_audio_transcription(self, lesson_id: int) -> str:
        """
        Generate (mock) audio transcription for a lesson.
        
        Args:
            lesson_id: ID of the lesson
            
        Returns:
            URL to the mock audio transcription
        """
        # In a real implementation, this would call a TTS service
        return f"https://storage.example.com/audio/lessons/{lesson_id}.mp3"
        
    async def update_content_markdown(self, lesson_id: int, content_update: str) -> Optional[Lesson]:
        """
        Update the markdown content of a lesson.
        
        Args:
            lesson_id: ID of the lesson
            content_update: New markdown content
            
        Returns:
            Updated lesson
        """
        lesson = await self.repository.get_by_id(lesson_id)
        if not lesson:
            return None
            
        lesson.content = content_update
        return await self.repository.update(lesson)

    async def get_lesson(self, lesson_id: int) -> Optional[Lesson]:
        """Get lesson by ID."""
        return await self.repository.get_by_id(lesson_id)
