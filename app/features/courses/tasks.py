import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.events import LogEvent, LogLevel, event_bus
from app.common.database.session import AsyncSessionLocal
from app.features.courses.repository import (
    CourseRepository,
    UserCourseRepository,
    CategoryRepository,
    SubCategoryRepository,
)
from app.features.modules.repository import ModuleRepository
from app.features.lessons.repository import LessonRepository
from app.features.reviews.repository import ReviewRepository
from app.common.dependencies import get_firebase_storage_service, get_image_generation_service
from app.features.courses.service import CourseService


def _get_course_service(session: AsyncSession) -> CourseService:
    """Helper to create a CourseService instance with a specific session."""
    return CourseService(
        course_repository=CourseRepository(session),
        module_repository=ModuleRepository(session),
        lesson_repository=LessonRepository(session),
        user_course_repository=UserCourseRepository(session),
        review_repository=ReviewRepository(session),
        category_repository=CategoryRepository(session),
        subcategory_repository=SubCategoryRepository(session),
        storage_service=get_firebase_storage_service(),
        image_gen_service=get_image_generation_service(),
    )


async def generate_course_image_background(
    course_id: int
):
    """
    Background task to generate an image for a course.
    """
    try:
        async with AsyncSessionLocal() as session:
            course_service = _get_course_service(session)

            # Fetch course to check if image already exists
            course = await course_service.repository.get_by_id(course_id)

            if not course:
                print(f"Course {course_id} not found during background image generation.")
                return

            if course.image_url:
                print(f"Image already exists for course {course_id}.")
                return

            print(f"Generating image for course {course_id}...")
            await course_service.generate_course_image(course_id)
            await course_service.commit_all()
            print(f"Image generation completed for course {course_id}")

    except Exception as e:
        traceback.print_exc()
        print(f"Failed to generate image for course {course_id}: {str(e)}")
        # Note: we don't dispatch the event with event_bus inside the transaction block to avoid using a closed session,
        # but we can dispatch it since EventBus does not depend on DB session
        await event_bus.dispatch(
            LogEvent(
                level=LogLevel.ERROR,
                message=f"Failed to generate image for course {course_id}: {str(e)}",
                data={
                    "course_id": course_id,
                    "error": str(e),
                    "stacktrace": traceback.format_exc(),
                },
            )
        )
