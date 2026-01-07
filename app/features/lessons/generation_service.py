"""Service for generating lesson content using AI."""
from typing import Optional
from app.services.langchain_service import langchain_service
from app.features.courses.models import Course
from app.features.modules.models import Module
from app.features.lessons.models import Lesson

class LessonGenerationService:
    """Service for generating lesson content."""
    
    def __init__(self):
        self.ai_service = langchain_service
        
    async def generate_lesson_content(
        self,
        course: Course,
        module: Module,
        lesson: Lesson
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
Start directly with the introduction or the first section."""

        user_prompt = f"""Create content for the following lesson:

Course: {course.title}
Course Description: {course.description}

Module: {module.title}
Module Description: {module.description or 'N/A'}

Lesson: {lesson.title}
Lesson Description: {lesson.description or 'N/A'}
Objectives: {lesson.objectives or 'N/A'}

Please provide a detailed lesson that covers the topic thoroughly.
Include:
1. Introduction
2. Key Concepts
3. Detailed Explanation with Examples
4. Practical Application / Exercises
5. Summary

Format as distinct Markdown sections."""

        content = await self.ai_service.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return str(content)

# Singleton instance
lesson_generation_service = LessonGenerationService()
