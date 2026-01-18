"""Quiz and Question repositories for database operations."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from app.features.quiz.models import Quiz, Question


class QuizRepository:
    """Repository for quiz database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, quiz_id: int) -> Optional[Quiz]:
        """Get quiz by ID with questions."""
        result = await self.session.execute(
            select(Quiz).where(Quiz.id == quiz_id).options(selectinload(Quiz.questions))  # type: ignore
        )
        return result.scalar_one_or_none()

    async def get_by_lesson_id(self, lesson_id: int) -> Optional[Quiz]:
        """Get quiz by lesson ID with questions."""
        result = await self.session.execute(
            select(Quiz)
            .where(Quiz.lesson_id == lesson_id)
            .options(selectinload(Quiz.questions))  # type: ignore
        )
        return result.scalar_one_or_none()

    async def create(self, quiz: Quiz) -> Quiz:
        """Create a new quiz."""
        self.session.add(quiz)
        await self.session.flush()
        await self.session.refresh(quiz)
        return quiz

    async def update(self, quiz: Quiz) -> Quiz:
        """Update an existing quiz."""
        self.session.add(quiz)
        await self.session.flush()
        await self.session.refresh(quiz)
        return quiz

    async def delete(self, quiz: Quiz) -> None:
        """Delete a quiz."""
        await self.session.delete(quiz)
        await self.session.flush()


class QuestionRepository:
    """Repository for question database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, question_id: int) -> Optional[Question]:
        """Get question by ID."""
        result = await self.session.execute(
            select(Question).where(Question.id == question_id)
        )
        return result.scalar_one_or_none()

    async def get_by_quiz_id(self, quiz_id: int) -> List[Question]:
        """Get all questions for a quiz."""
        result = await self.session.execute(
            select(Question).where(Question.quiz_id == quiz_id)
        )
        return list(result.scalars().all())

    async def create(self, question: Question) -> Question:
        """Create a new question."""
        self.session.add(question)
        await self.session.flush()
        await self.session.refresh(question)
        return question

    async def update(self, question: Question) -> Question:
        """Update an existing question."""
        self.session.add(question)
        await self.session.flush()
        await self.session.refresh(question)
        return question

    async def delete(self, question: Question) -> None:
        """Delete a question."""
        await self.session.delete(question)
        await self.session.flush()
