import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.maintenance_service import DBMaintenanceService
from app.features.lessons.models import LessonAudio
from app.features.courses.models import Course


@pytest.fixture
def mock_audio_repo():
    repo = AsyncMock()
    repo.session = AsyncMock()
    return repo


@pytest.fixture
def mock_course_repo():
    repo = AsyncMock()
    repo.session = AsyncMock()
    return repo


@pytest.fixture
def mock_storage_service():
    return MagicMock()


@pytest.fixture
def maintenance_service(mock_audio_repo, mock_course_repo, mock_storage_service):
    return DBMaintenanceService(
        audio_repo=mock_audio_repo,
        course_repo=mock_course_repo,
        storage_service=mock_storage_service,
    )


@pytest.mark.asyncio
async def test_cleanup_orphaned_audios_success(
    maintenance_service, mock_audio_repo, mock_storage_service
):
    # Setup
    mock_audio = MagicMock(spec=LessonAudio)
    mock_audio.id = 1
    mock_audio.audio_url = "https://example.com/audio.mp3"

    mock_audio_repo.get_orphaned_audios.return_value = [mock_audio]
    mock_storage_service.delete_file.return_value = True

    # Execute
    result = await maintenance_service.cleanup_orphaned_audios()

    # Assert
    assert result["orphans_found"] == 1
    assert result["storage_deleted"] == 1
    assert result["db_deleted"] == 1

    mock_audio_repo.get_orphaned_audios.assert_called_once()
    mock_storage_service.delete_file.assert_called_once_with(mock_audio.audio_url)
    mock_audio_repo.delete.assert_called_once_with(mock_audio)
    mock_audio_repo.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_orphaned_audios_no_orphans(
    maintenance_service, mock_audio_repo, mock_storage_service
):
    # Setup
    mock_audio_repo.get_orphaned_audios.return_value = []

    # Execute
    result = await maintenance_service.cleanup_orphaned_audios()

    # Assert
    assert result["deleted_count"] == 0
    assert result["storage_deleted"] == 0
    mock_audio_repo.get_orphaned_audios.assert_called_once()
    mock_storage_service.delete_file.assert_not_called()
    mock_audio_repo.delete.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_orphaned_courses_success(
    maintenance_service, mock_course_repo, mock_storage_service
):
    # Setup
    mock_course = MagicMock(spec=Course)
    mock_course.id = 1
    mock_course.image_url = "https://example.com/image.jpg"

    mock_course_repo.get_orphaned_courses.return_value = [mock_course]
    mock_storage_service.delete_file.return_value = True

    # Execute
    result = await maintenance_service.cleanup_orphaned_courses()

    # Assert
    assert result["orphans_found"] == 1
    assert result["storage_deleted"] == 1
    assert result["db_deleted"] == 1

    mock_course_repo.get_orphaned_courses.assert_called_once()
    mock_storage_service.delete_file.assert_called_once_with(mock_course.image_url)
    mock_course_repo.delete.assert_called_once_with(mock_course)
    mock_course_repo.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_run_all_maintenance(
    maintenance_service, mock_audio_repo, mock_course_repo
):
    # Setup
    mock_audio_repo.get_orphaned_audios.return_value = []
    mock_course_repo.get_orphaned_courses.return_value = []

    # Execute
    result = await maintenance_service.run_all_maintenance()

    # Assert
    assert "audios" in result
    assert "courses" in result
    mock_audio_repo.get_orphaned_audios.assert_called_once()
    mock_course_repo.get_orphaned_courses.assert_called_once()
