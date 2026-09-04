import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.lessons.generation_tracker_service import (
    LessonGenerationTrackerService,
)
from app.features.lessons.models import (
    LessonGenerationState,
    GenerationType,
    GenerationStatus,
)


@pytest.mark.asyncio
async def test_lesson_generation_tracker_service_unit_start_and_complete():
    """Unit test start_tracking and complete_tracking with AsyncMock session."""
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Mock execute return value for active generation query (returns None -> no active generation)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    service = LessonGenerationTrackerService(mock_session)
    user_id = 1
    lesson_id = 101

    # Start tracking
    started, state = await service.start_tracking(
        user_id=user_id,
        lesson_id=lesson_id,
        generation_type=GenerationType.CONTENT,
        task_id="task-123",
        metadata={"mode": "test"},
    )

    assert started is True
    assert state.user_id == user_id
    assert state.lesson_id == lesson_id
    assert state.generation_type == GenerationType.CONTENT
    assert state.status == GenerationStatus.IN_PROGRESS
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()

    # Complete tracking
    mock_result_state = MagicMock()
    mock_result_state.scalar_one_or_none.return_value = state
    mock_session.execute.return_value = mock_result_state

    completed_state = await service.complete_tracking(
        generation_type=GenerationType.CONTENT,
        lesson_id=lesson_id,
    )

    assert completed_state is not None
    assert completed_state.status == GenerationStatus.COMPLETED
    assert completed_state.completed_at is not None


@pytest.mark.asyncio
async def test_lesson_generation_tracker_service_unit_duplicate_check():
    """Unit test that start_tracking returns False if generation is already in progress."""
    mock_session = AsyncMock(spec=AsyncSession)

    existing_state = LessonGenerationState(
        id=55,
        user_id=1,
        lesson_id=101,
        generation_type=GenerationType.CONTENT,
        status=GenerationStatus.IN_PROGRESS,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_state
    mock_session.execute.return_value = mock_result

    service = LessonGenerationTrackerService(mock_session)
    started, state = await service.start_tracking(
        user_id=1,
        lesson_id=101,
        generation_type=GenerationType.CONTENT,
    )

    assert started is False
    assert state.id == 55
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_lesson_generation_tracker_service_unit_fail_tracking():
    """Unit test fail_tracking with AsyncMock session."""
    mock_session = AsyncMock(spec=AsyncSession)

    state = LessonGenerationState(
        id=88,
        user_id=2,
        lesson_id=202,
        generation_type=GenerationType.AUDIO,
        status=GenerationStatus.IN_PROGRESS,
        provider="elevenlabs",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = state
    mock_session.execute.return_value = mock_result

    service = LessonGenerationTrackerService(mock_session)
    failed_state = await service.fail_tracking(
        generation_type=GenerationType.AUDIO,
        lesson_id=202,
        error_message="Audio service error",
    )

    assert failed_state is not None
    assert failed_state.status == GenerationStatus.FAILED
    assert failed_state.error_message == "Audio service error"
    assert failed_state.completed_at is not None


@pytest.mark.asyncio
async def test_get_generation_states_by_lesson_id_statuses_filter():
    """Unit test get_generation_states_by_lesson_id with status list filtering."""
    mock_session = AsyncMock(spec=AsyncSession)

    state1 = LessonGenerationState(
        id=1,
        user_id=10,
        lesson_id=303,
        generation_type=GenerationType.CONTENT,
        status=GenerationStatus.COMPLETED,
    )
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [state1]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = LessonGenerationTrackerService(mock_session)
    states = await service.get_generation_states_by_lesson_id(
        lesson_id=303,
        generation_type=GenerationType.CONTENT,
        statuses=["completed", "in_progress"],
    )

    assert len(states) == 1
    assert states[0].status == GenerationStatus.COMPLETED
    mock_session.execute.assert_called_once()



