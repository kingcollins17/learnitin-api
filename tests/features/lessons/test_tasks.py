import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.features.lessons.tasks import generate_audio_background
from app.common.events import LogEvent, LogLevel, AudioGenerationFailedEvent

@pytest.mark.asyncio
async def test_generate_audio_background_error_handling():
    # Arrange
    lesson_id = 999
    user_id = 123
    
    lesson_service = MagicMock()
    # Mocking get_lesson_by_id to raise an exception
    lesson_service.get_lesson_by_id = AsyncMock(side_effect=ValueError("Test database error"))
    
    credit_service = MagicMock()
    
    # We patch event_bus.dispatch to track calls
    with patch("app.features.lessons.tasks.event_bus.dispatch", new_callable=AsyncMock) as mock_dispatch:
        # Act
        await generate_audio_background(
            lesson_id=lesson_id,
            lesson_service=lesson_service,
            credit_service=credit_service,
            user_id=user_id,
        )
        
        # Assert
        # Check that event_bus.dispatch was called twice (AudioGenerationFailedEvent and LogEvent)
        assert mock_dispatch.call_count == 2
        
        # Check AudioGenerationFailedEvent was dispatched
        failed_event_call = mock_dispatch.call_args_list[0][0][0]
        assert isinstance(failed_event_call, AudioGenerationFailedEvent)
        assert failed_event_call.user_id == user_id
        assert failed_event_call.lesson_id == lesson_id
        assert "Test database error" in failed_event_call.error
        
        # Check LogEvent was dispatched
        log_event_call = mock_dispatch.call_args_list[1][0][0]
        assert isinstance(log_event_call, LogEvent)
        assert log_event_call.level == LogLevel.ERROR
        assert "Failed to generate audio for lesson 999" in log_event_call.message
        assert log_event_call.data is not None
        assert log_event_call.data["lesson_id"] == lesson_id
        assert log_event_call.data["user_id"] == user_id
        assert log_event_call.data["error"] == "Test database error"
        assert "traceback" in log_event_call.data["stacktrace"].lower()
