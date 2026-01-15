import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.courses.service import CourseService


async def generate_course_image_background(course_id: int, session: AsyncSession):
    """
    Background task to generate an image for a course.
    """
    try:
        course_service = CourseService(session)
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
        print(f"Image generation completed for course {course_id}")

    except Exception as e:
        traceback.print_exc()
        print(f"Failed to generate image for course {course_id}: {str(e)}")
