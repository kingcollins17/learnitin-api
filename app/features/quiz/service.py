"""Business logic for Quizzes."""

from sqlalchemy.ext.asyncio import AsyncSession
from app.features.quiz.repository import QuizRepository, QuestionRepository
from app.features.quiz.generation_service import quiz_generation_service
from app.features.quiz.models import Quiz, Question
from app.features.lessons.models import Lesson
from app.common.events import event_bus, QuizGeneratedEvent
import logging

logger = logging.getLogger(__name__)


class QuizService:
    """Service for managing quizzes."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.quiz_repo = QuizRepository(session)
        self.question_repo = QuestionRepository(session)

    async def generate_and_save_quiz(
        self, lesson: Lesson, question_count: int = 10
    ) -> Quiz:
        """
        Generate a quiz for a lesson, save it to database, and dispatch event.

        Args:
            lesson: The lesson to generate a quiz for
            question_count: Number of questions to generate

        Returns:
            The created Quiz object with questions
        """
        logger.info(f"Generating quiz for lesson: {lesson.id}")

        # 1. Generate quiz data using AI
        quiz_data = await quiz_generation_service.generate_quiz(
            lesson=lesson, question_count=question_count
        )
        print(f"Quiz generated for lesson {lesson.title}")
        # 2. Create Quiz record
        quiz = Quiz(
            lesson_id=lesson.id,
            duration=quiz_data.duration_seconds,
            passing_score=quiz_data.passing_score_ratio,
        )
        created_quiz = await self.quiz_repo.create(quiz)

        # 3. Create Question records
        assert created_quiz.id is not None
        for q_data in quiz_data.questions:
            question = Question(
                quiz_id=created_quiz.id,
                lesson_id=lesson.id,
                question=q_data.question,
                option_1=q_data.option_1,
                option_2=q_data.option_2,
                option_3=q_data.option_3,
                option_4=q_data.option_4,
                correct_option_index=q_data.correct_option_index,
                explanation=q_data.explanation,
            )
            await self.question_repo.create(question)

        # 4. Commit all changes
        await self.session.commit()

        # 5. Dispatch event
        quiz_id = created_quiz.id
        assert quiz_id is not None
        event = QuizGeneratedEvent(
            quiz_id=quiz_id,
            lesson_id=lesson.id,
            question_count=len(quiz_data.questions),
        )
        event_bus.dispatch(event)

        # 6. Reload with questions populated
        final_quiz = await self.quiz_repo.get_by_id(quiz_id)
        assert final_quiz is not None
        return final_quiz

    async def get_quiz_by_lesson(self, lesson_id: int) -> Quiz | None:
        """Get quiz for a specific lesson."""
        return await self.quiz_repo.get_by_lesson_id(lesson_id)
