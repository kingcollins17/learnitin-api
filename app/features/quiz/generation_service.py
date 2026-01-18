"""Service for generating quiz content using AI."""

from typing import Optional
from app.services.langchain_service import langchain_service
from app.features.lessons.models import Lesson
from app.features.quiz.schemas import QuizGenerationSchema


class QuizGenerationService:
    """Service for generating quizzes from lesson content."""

    def __init__(self):
        self.ai_service = langchain_service

    async def generate_quiz(
        self, lesson: Lesson, question_count: int = 10
    ) -> QuizGenerationSchema:
        """
        Generate a quiz for a lesson using AI.

        Args:
            lesson: The lesson to generate a quiz for
            question_count: Number of questions to generate

        Returns:
            Structured quiz data
        """
        system_prompt = """You are an expert educational assessment creator.
Your task is to create high-quality, challenging but fair multiple-choice questions based on the provided lesson content.
Focus on testing understanding of key concepts, practical application, and critical thinking.
Ensure each question has exactly 4 options and one clearly correct answer.
Provide a clear explanation for each answer."""

        user_prompt = """Generate a quiz for the following lesson:

Title: {title}
Content:
{content}

Requirements:
- Number of questions: {count}
- Each question must have 4 options.
- The questions should cover different aspects of the lesson.
- Provide a recommended duration in seconds based on the difficulty and number of questions.
- Set a default passing score ratio of 0.7 unless the content implies a higher requirement."""

        quiz_data = await self.ai_service.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=QuizGenerationSchema,
            title=lesson.title,
            content=lesson.content,
            count=question_count,
        )

        return quiz_data  # type: ignore


# Singleton instance
quiz_generation_service = QuizGenerationService()
