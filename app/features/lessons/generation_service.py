"""Service for generating lesson content using AI."""

from typing import Optional
from app.services.langchain_service import LangChainService
from app.features.courses.models import Course
from app.features.modules.models import Module
from app.features.lessons.models import Lesson


class LessonGenerationService:
    """Service for generating lesson content."""

    def __init__(self, ai_service: LangChainService):
        self.ai_service = ai_service

    async def generate_lesson_content(
        self, course: Course, module: Module, lesson: Lesson
    ) -> str:
        """
        Generate content for a lesson using AI.

        Args:
            course: The course the lesson belongs to
            module: The module the lesson belongs to
            lesson: The lesson to generate content for

        Returns:
            Generated markdown content
        """
        system_prompt = """You are an expert educational content creator. 
Your task is to create comprehensive, engaging, and well-structured lesson content in Markdown format.
Focus on clarity, educational value, and practical examples.
Structure the content with clear headings, bullet points, and code blocks where appropriate.
Do not include the lesson title as a top-level heading, as it will be displayed separately.

MOBILE READABILITY:
Avoid using Markdown tables as they wrap poorly on narrow mobile screens. 
Instead, use descriptive lists, nested bullet points, or separate sections for comparisons. 
If a tabular format is absolutely essential for the data, ensure it is structured simply or suggest horizontal scrolling by providing the content in a way that respects mobile width constraints.

IMPORTANT: Adapt the content structure to fit the lesson's specific description and objectives.
Different lessons require different approaches - some may need step-by-step tutorials, others may need 
conceptual explanations, comparisons, case studies, or hands-on exercises. Choose the most appropriate 
structure and sections based on what will best help learners achieve the stated objectives."""

        user_prompt = f"""Create content for the following lesson:

Course: {course.title}
Course Description: {course.description}

Module: {module.title}
Module Description: {module.description or 'N/A'}

Lesson: {lesson.title}
Lesson Description: {lesson.description or 'N/A'}
Objectives: {lesson.objectives or 'N/A'}

Based on the lesson description and objectives above, structure the content in the most appropriate way 
to help learners achieve these specific goals. The structure should be tailored to this particular lesson's 
needs rather than following a rigid template. Use clear Markdown sections with descriptive headings."""

        content = await self.ai_service.invoke(
            system_prompt=system_prompt, user_prompt=user_prompt
        )

        return str(content)
