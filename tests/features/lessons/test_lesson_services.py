"""Tests for Lesson services."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.models import User
from app.features.courses.models import Course
from app.features.modules.models import Module
from app.features.lessons.models import Lesson
from app.features.lessons.service import LessonService
from app.features.lessons.generation_service import LessonGenerationService

@pytest.fixture
async def mock_db_data(db_session: AsyncSession):
    """Create mock data in DB."""
    user = User(email="service_test@example.com", username="servicetest", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()
    
    course = Course(title="Service Course", description="Desc", user_id=user.id, duration="1h")
    db_session.add(course)
    await db_session.flush()
    
    module = Module(title="Service Module", course_id=course.id, module_slug="svc-mod", order=1)
    db_session.add(module)
    await db_session.flush()
    
    lesson = Lesson(title="Service Lesson", course_id=course.id, module_id=module.id, order=1)
    db_session.add(lesson)
    await db_session.commit()
    
    return lesson.id

@pytest.mark.asyncio
async def test_lesson_generation_service():
    """Test LessonGenerationService."""
    service = LessonGenerationService()
    
    # Mock models
    course = MagicMock(spec=Course)
    course.title = "Test Course"
    course.description = "Test Desc"
    
    module = MagicMock(spec=Module)
    module.title = "Test Module"
    module.description = "Test Mod Desc"
    
    lesson = MagicMock(spec=Lesson)
    lesson.title = "Test Lesson"
    lesson.description = "Test Less Desc"
    lesson.objectives = "Learn stuff"
    
    # Mock langchain service
    with patch.object(service.ai_service, 'invoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = "# Generated Content"
        
        content = await service.generate_lesson_content(course, module, lesson)
        
        assert content == "# Generated Content"
        mock_invoke.assert_called_once()
        call_kwargs = mock_invoke.call_args[1]
        assert "Test Course" in call_kwargs['user_prompt']
        assert "Test Module" in call_kwargs['user_prompt']
        assert "Test Lesson" in call_kwargs['user_prompt']

@pytest.mark.asyncio
async def test_lesson_service_generate_content(db_session: AsyncSession, mock_db_data):
    """Test LessonService.generate_content."""
    lesson_id = mock_db_data
    service = LessonService(db_session)
    
    # Mock generation service
    with patch.object(service.generation_service, 'generate_lesson_content', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Updated Content from AI"
        
        updated_lesson = await service.generate_content(lesson_id)
        
        assert updated_lesson is not None
        assert updated_lesson.content == "Updated Content from AI"
        mock_gen.assert_called_once()

@pytest.mark.asyncio
async def test_lesson_service_audio_transcription(db_session: AsyncSession):
    """Test LessonService.generate_audio_transcription."""
    service = LessonService(db_session)
    url = await service.generate_audio_transcription(123)
    assert url == "https://storage.example.com/audio/lessons/123.mp3"

@pytest.mark.asyncio
async def test_lesson_service_update_markdown(db_session: AsyncSession, mock_db_data):
    """Test LessonService.update_content_markdown."""
    lesson_id = mock_db_data
    service = LessonService(db_session)
    
    updated = await service.update_content_markdown(lesson_id, "New Manual Content")
    
    assert updated is not None
    assert updated.content == "New Manual Content"
