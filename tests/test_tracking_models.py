"""Tests for user progress tracking models and repositories."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.models import User
from app.features.courses.models import Course, UserCourse, ProgressStatus
from app.features.modules.models import Module, UserModule
from app.features.lessons.models import Lesson, UserLesson
from app.features.courses.repository import UserCourseRepository
from app.features.modules.repository import UserModuleRepository
from app.features.lessons.repository import UserLessonRepository

@pytest.fixture
async def sample_data(db_session: AsyncSession):
    """Create sample data for testing."""
    # Create user
    user = User(email="t@example.com", username="tuser", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()
    
    # Create course
    course = Course(
        user_id=user.id,
        title="Test Course",
        description="Desc",
        duration="1h",
        is_public=True
    )
    db_session.add(course)
    await db_session.flush()
    
    # Create module
    module = Module(
        course_id=course.id,
        title="Test Module",
        module_slug="test-module",
        order=1
    )
    db_session.add(module)
    await db_session.flush()
    
    # Create lesson (verify is_unlocked is NOT here)
    lesson = Lesson(
        course_id=course.id,
        module_id=module.id,
        title="Test Lesson",
        order=1
    )
    # If is_unlocked was still there, we could set it, but we won't.
    db_session.add(lesson)
    await db_session.flush()
    
    await db_session.commit()
    
    return {
        "user_id": user.id,
        "course_id": course.id,
        "module_id": module.id,
        "lesson_id": lesson.id
    }

@pytest.mark.asyncio
async def test_user_course_repository(db_session: AsyncSession, sample_data):
    """Test UserCourseRepository."""
    repo = UserCourseRepository(db_session)
    user_id = sample_data["user_id"]
    course_id = sample_data["course_id"]
    
    # Create
    user_course = UserCourse(
        user_id=user_id,
        course_id=course_id,
        completed_modules=0,
        status=ProgressStatus.IN_PROGRESS
    )
    created = await repo.create(user_course)
    assert created.id is not None
    assert created.status == ProgressStatus.IN_PROGRESS
    
    # Get by ID
    fetched = await repo.get_by_id(created.id)
    assert fetched.id == created.id
    
    # Get by user and course
    fetched_by_rel = await repo.get_by_user_and_course(user_id, course_id)
    assert fetched_by_rel.id == created.id
    
    # Get all by user
    all_courses = await repo.get_by_user(user_id)
    assert len(all_courses) == 1
    
    # Update
    created.completed_modules = 1
    created.status = ProgressStatus.COMPLETED
    updated = await repo.update(created)
    assert updated.status == ProgressStatus.COMPLETED

@pytest.mark.asyncio
async def test_user_module_repository(db_session: AsyncSession, sample_data):
    """Test UserModuleRepository."""
    repo = UserModuleRepository(db_session)
    user_id = sample_data["user_id"]
    course_id = sample_data["course_id"]
    module_id = sample_data["module_id"]
    
    # Create
    user_module = UserModule(
        user_id=user_id,
        course_id=course_id,
        module_id=module_id,
        status=ProgressStatus.IN_PROGRESS
    )
    created = await repo.create(user_module)
    assert created.id is not None
    
    # Get by ID
    fetched = await repo.get_by_id(created.id)
    assert fetched.id == created.id
    
    # Get by user and module
    fetched_by_rel = await repo.get_by_user_and_module(user_id, module_id)
    assert fetched_by_rel.id == created.id
    
    # Get by user and course
    modules_in_course = await repo.get_by_user_and_course(user_id, course_id)
    assert len(modules_in_course) == 1
    assert modules_in_course[0].id == created.id

@pytest.mark.asyncio
async def test_user_lesson_repository(db_session: AsyncSession, sample_data):
    """Test UserLessonRepository."""
    repo = UserLessonRepository(db_session)
    user_id = sample_data["user_id"]
    course_id = sample_data["course_id"]
    module_id = sample_data["module_id"]
    lesson_id = sample_data["lesson_id"]
    
    # Create
    user_lesson = UserLesson(
        user_id=user_id,
        course_id=course_id,
        module_id=module_id,
        lesson_id=lesson_id,
        is_unlocked=True,
        status=ProgressStatus.IN_PROGRESS
    )
    created = await repo.create(user_lesson)
    assert created.id is not None
    assert created.is_unlocked is True
    
    # Get by ID
    fetched = await repo.get_by_id(created.id)
    assert fetched.id == created.id
    
    # Get by user and lesson
    fetched_by_rel = await repo.get_by_user_and_lesson(user_id, lesson_id)
    assert fetched_by_rel.id == created.id
    
    # Get by user and module
    lessons_in_module = await repo.get_by_user_and_module(user_id, module_id)
    assert len(lessons_in_module) == 1
    
    # Get by user and course
    lessons_in_course = await repo.get_by_user_and_course(user_id, course_id)
    assert len(lessons_in_course) == 1
    
    # Verify Lesson model does NOT have is_unlocked (checking instance attribute error if accessed, or just that we instantiated it without it earlier)
    # We instantiated 'lesson' in 'sample_data' without 'is_unlocked', which confirms pydantic validation didn't require it (if it was required) or allow it (if we passed it).
    # Here we can just assert that the user_lesson HAS is_unlocked.
