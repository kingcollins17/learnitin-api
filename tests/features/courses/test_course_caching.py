import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.courses.models import Course
from app.features.courses.repository import (
    CourseRepository,
    COURSE_BY_ID_CACHE,
    COURSE_WITH_MODULES_CACHE,
)
from app.common.cache import cache_service


@pytest.mark.asyncio
async def test_course_repository_caching(db_session: AsyncSession):
    """Test caching behavior of CourseRepository."""
    # Setup - Clear cache first
    cache_service.clear(COURSE_BY_ID_CACHE)
    cache_service.clear(COURSE_WITH_MODULES_CACHE)

    # Create a course
    course = Course(
        title="Caching Python Course",
        description="Learn Python caching",
        level="beginner",
        duration="4 weeks",
        is_public=True,
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    repo = CourseRepository(db_session)

    # 1. Verify cache is initially empty
    assert not cache_service.has(COURSE_BY_ID_CACHE, course.id)

    # 2. Get course - should populate cache
    fetched = await repo.get_by_id(course.id)
    assert fetched is not None
    assert fetched.title == "Caching Python Course"
    assert cache_service.has(COURSE_BY_ID_CACHE, course.id)

    # 3. Verify cache hit by checking cached contents
    cached_course = cache_service.get(COURSE_BY_ID_CACHE, course.id)
    assert cached_course is not None
    assert cached_course.id == course.id

    # 4. Modify course description directly in DB bypassing update method
    # so we can verify cache hit returns old value.
    # We expunge the fetched object from the session so the session doesn't mutate it.
    db_session.expunge(fetched)

    from sqlalchemy import update
    await db_session.execute(
        update(Course).where(Course.id == course.id).values(description="Direct DB edit")
    )
    await db_session.commit()

    # Get course (use_cache=True, default) - should return cached version (stale)
    fetched_cached = await repo.get_by_id(course.id)
    assert fetched_cached.description == "Learn Python caching"

    # Get course (use_cache=False) - should query DB and update cache (fresh)
    fetched_db = await repo.get_by_id(course.id, use_cache=False)
    assert fetched_db.description == "Direct DB edit"
    assert cache_service.get(COURSE_BY_ID_CACHE, course.id).description == "Direct DB edit"

    # 5. Update course using repo.update - should invalidate cache
    fetched_db.title = "Caching Course 2.0"
    await repo.update(fetched_db)

    # Cache should be invalidated
    assert not cache_service.has(COURSE_BY_ID_CACHE, course.id)

    # 6. Manual Invalidation
    # Repopulate cache
    await repo.get_by_id(course.id)
    assert cache_service.has(COURSE_BY_ID_CACHE, course.id)
    
    # Manually invalidate
    CourseRepository.invalidate_cache(course.id)
    assert not cache_service.has(COURSE_BY_ID_CACHE, course.id)

    # 7. Delete course - should also invalidate cache
    # Repopulate
    fetched_again = await repo.get_by_id(course.id)
    assert cache_service.has(COURSE_BY_ID_CACHE, course.id)

    await repo.delete(fetched_again)
    assert not cache_service.has(COURSE_BY_ID_CACHE, course.id)


@pytest.mark.asyncio
async def test_course_list_caching(db_session: AsyncSession):
    """Test caching behavior of list-based queries in CourseRepository."""
    from app.features.courses.repository import (
        COURSE_LIST_ALL_CACHE,
        COURSE_LIST_BY_USER_CACHE,
        COURSE_LIST_ORPHANED_CACHE,
        COURSE_LIST_FILTERED_CACHE,
    )

    # Setup - Clear caches
    cache_service.clear(COURSE_LIST_ALL_CACHE)
    cache_service.clear(COURSE_LIST_BY_USER_CACHE)
    cache_service.clear(COURSE_LIST_ORPHANED_CACHE)
    cache_service.clear(COURSE_LIST_FILTERED_CACHE)

    # Create a course
    course = Course(
        title="Caching Python Course List",
        description="Learn list caching",
        level="beginner",
        duration="4 weeks",
        is_public=False,  # Private to test orphaned courses caching
        user_id=None,
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    repo = CourseRepository(db_session)

    # 1. Test get_all list caching
    assert not cache_service.has(COURSE_LIST_ALL_CACHE, (0, 100))
    all_courses = await repo.get_all(0, 100)
    assert len(all_courses) > 0
    assert cache_service.has(COURSE_LIST_ALL_CACHE, (0, 100))

    # 2. Test get_orphaned_courses caching
    assert not cache_service.has(COURSE_LIST_ORPHANED_CACHE, "orphaned")
    orphaned = await repo.get_orphaned_courses()
    assert len(orphaned) > 0
    assert cache_service.has(COURSE_LIST_ORPHANED_CACHE, "orphaned")

    # 3. Test get_all_with_filters caching
    filter_key = (0, 100, False, "beginner", None, None, None, None)
    assert not cache_service.has(COURSE_LIST_FILTERED_CACHE, filter_key)
    filtered = await repo.get_all_with_filters(0, 100, is_public=False, level="beginner")
    assert len(filtered) > 0
    assert cache_service.has(COURSE_LIST_FILTERED_CACHE, filter_key)

    # 4. Invalidate caches via new course creation
    new_course = Course(
        title="Another Course",
        description="Invalidates caches",
        level="beginner",
        duration="1 week",
        is_public=True,
    )
    await repo.create(new_course)

    # Caches should be cleared
    assert not cache_service.has(COURSE_LIST_ALL_CACHE, (0, 100))
    assert not cache_service.has(COURSE_LIST_ORPHANED_CACHE, "orphaned")
    assert not cache_service.has(COURSE_LIST_FILTERED_CACHE, filter_key)

