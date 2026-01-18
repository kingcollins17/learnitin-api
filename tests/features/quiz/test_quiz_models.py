"""Tests for Quiz and Question models and repositories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.models import User
from app.features.courses.models import Course
from app.features.modules.models import Module
from app.features.lessons.models import Lesson
from app.features.quiz.models import Quiz, Question
from app.features.quiz.repository import QuizRepository, QuestionRepository


@pytest.fixture
async def lesson_fixture(db_session: AsyncSession):
    """Create a lesson fixture."""
    user = User(
        email="quiz_test@example.com", username="quiztest", hashed_password="pw"
    )
    db_session.add(user)
    await db_session.flush()

    course = Course(
        title="Quiz Course", description="Desc", user_id=user.id, duration="1h"
    )
    db_session.add(course)
    await db_session.flush()

    module = Module(
        title="Quiz Module", course_id=course.id, module_slug="quiz-mod", order=1
    )
    db_session.add(module)
    await db_session.flush()

    lesson = Lesson(
        title="Quiz Lesson", course_id=course.id, module_id=module.id, order=1
    )
    db_session.add(lesson)
    await db_session.commit()
    return lesson


@pytest.mark.asyncio
async def test_quiz_repository(db_session: AsyncSession, lesson_fixture):
    """Test QuizRepository."""
    repo = QuizRepository(db_session)
    lesson = lesson_fixture

    # Create
    quiz = Quiz(lesson_id=lesson.id, duration=1800, passing_score=0.8)  # 30 mins
    created = await repo.create(quiz)
    assert created.id is not None
    assert created.duration == 1800

    # Get by ID
    assert created.id is not None
    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id

    # Get by Lesson ID
    fetched_by_lesson = await repo.get_by_lesson_id(lesson.id)
    assert fetched_by_lesson is not None
    assert fetched_by_lesson.id == created.id

    # Update
    created.passing_score = 0.9
    updated = await repo.update(created)
    assert updated.passing_score == 0.9


@pytest.mark.asyncio
async def test_quiz_unique_lesson_constraint(db_session: AsyncSession, lesson_fixture):
    """Test that a lesson cannot have more than one quiz."""
    repo = QuizRepository(db_session)
    lesson = lesson_fixture

    # Create first quiz
    quiz1 = Quiz(lesson_id=lesson.id, duration=100)
    await repo.create(quiz1)

    # Try to create second quiz for same lesson
    quiz2 = Quiz(lesson_id=lesson.id, duration=200)
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await repo.create(quiz2)
        await db_session.commit()  # Need to commit to trigger the unique constraint check in some DBs, or session.flush()


@pytest.mark.asyncio
async def test_question_repository(db_session: AsyncSession, lesson_fixture):
    """Test QuestionRepository."""
    # Setup
    quiz_repo = QuizRepository(db_session)
    quiz = Quiz(lesson_id=lesson_fixture.id, duration=100)
    await quiz_repo.create(quiz)

    q_repo = QuestionRepository(db_session)

    # Create
    question = Question(
        quiz_id=quiz.id,
        lesson_id=lesson_fixture.id,
        question="What is 2+2?",
        option_1="3",
        option_2="4",
        option_3="5",
        option_4="6",
        explanation="Because 2 plus 2 equals 4.",
        correct_option_index=2,
    )
    created = await q_repo.create(question)
    assert created.id is not None
    assert created.explanation == "Because 2 plus 2 equals 4."
    assert created.question == "What is 2+2?"

    # Get by ID
    assert created.id is not None
    fetched = await q_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id

    # Get by Quiz ID
    assert quiz.id is not None
    questions = await q_repo.get_by_quiz_id(quiz.id)
    assert len(questions) == 1
    assert questions[0].id == created.id

    # Update
    created.question = "What is 2 * 2?"
    updated = await q_repo.update(created)
    assert updated.question == "What is 2 * 2?"
