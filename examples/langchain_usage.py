"""
Example usage of the LangChain service.

This file demonstrates how to use the LangChainService with:
- Basic text generation
- Structured output with Pydantic models
- Tool integration
- Context-based invocation
"""
import asyncio
from typing import List
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.services.langchain_service import LangChainService


# Example 1: Basic text generation
async def example_basic_usage():
    """Basic usage without structured output."""
    service = LangChainService(backend="gemini")
    
    response = await service.invoke(
        system_prompt="You are a helpful educational assistant for LearnItIn platform.",
        user_prompt="Explain what Python is in one sentence."
    )
    
    print("Basic Response:", response)


# Example 2: Structured output with Pydantic
class LearningPlan(BaseModel):
    """Structured learning plan response."""
    topic: str = Field(description="The learning topic")
    level: str = Field(description="Difficulty level")
    duration_weeks: int = Field(description="Estimated duration in weeks")
    modules: List[str] = Field(description="List of learning modules")
    prerequisites: List[str] = Field(description="Required prerequisites")


async def example_structured_output():
    """Using structured output with Pydantic models."""
    service = LangChainService(backend="gemini", temperature=0.5)
    
    response: LearningPlan = await service.invoke(
        system_prompt="You are an expert curriculum designer.",
        user_prompt="Create a learning plan for Python programming at beginner level.",
        response_schema=LearningPlan
    )
    
    print("\nStructured Response:")
    print(f"Topic: {response.topic}")
    print(f"Level: {response.level}")
    print(f"Duration: {response.duration_weeks} weeks")
    print(f"Modules: {', '.join(response.modules)}")
    print(f"Prerequisites: {', '.join(response.prerequisites)}")


# Example 3: Using tools
@tool
def calculate_study_hours(hours_per_day: int, days: int) -> int:
    """Calculate total study hours given hours per day and number of days."""
    return hours_per_day * days


async def example_with_tools():
    """Using LangChain tools with the service."""
    service = LangChainService(backend="gemini")
    
    response = await service.invoke(
        system_prompt="You are a study planner. Use the available tools to help users.",
        user_prompt="If I study 2 hours per day for 30 days, how many total hours is that?",
        tools=[calculate_study_hours]
    )
    
    print("\nResponse with Tools:", response)


# Example 4: Context-based invocation
async def example_with_context():
    """Using context for more informed responses."""
    service = LangChainService(backend="gemini")
    
    context = """
    User Profile:
    - Name: John Doe
    - Current Level: Beginner
    - Interests: Web Development, Python
    - Available Time: 10 hours/week
    """
    
    response = await service.invoke_with_context(
        system_prompt="You are a personalized learning advisor.",
        user_prompt="What should I learn next?",
        context=context
    )
    
    print("\nContext-based Response:", response)


# Example 5: Using different backends
async def example_multiple_backends():
    """Demonstrate using different backends."""
    # Using Gemini (default)
    gemini_service = LangChainService(backend="gemini")
    
    # Using OpenAI (if API key is configured)
    # openai_service = LangChainService(backend="openai", model="gpt-4")
    
    response = await gemini_service.invoke(
        system_prompt="You are a helpful assistant.",
        user_prompt="What is machine learning?"
    )
    
    print("\nGemini Response:", response)


# Example 6: Advanced structured output
class QuizQuestion(BaseModel):
    """A quiz question with multiple choices."""
    question: str = Field(description="The question text")
    options: List[str] = Field(description="List of 4 answer options")
    correct_answer: str = Field(description="The correct answer")
    explanation: str = Field(description="Explanation of the correct answer")


class Quiz(BaseModel):
    """A complete quiz."""
    title: str = Field(description="Quiz title")
    difficulty: str = Field(description="Difficulty level")
    questions: List[QuizQuestion] = Field(description="List of quiz questions")


async def example_complex_structured_output():
    """Generate a quiz with complex structured output."""
    service = LangChainService(backend="gemini", temperature=0.7)
    
    quiz: Quiz = await service.invoke(
        system_prompt="You are an expert quiz creator for educational platforms.",
        user_prompt="Create a 3-question quiz about Python basics for beginners.",
        response_schema=Quiz
    )
    
    print("\nGenerated Quiz:")
    print(f"Title: {quiz.title}")
    print(f"Difficulty: {quiz.difficulty}")
    print(f"\nQuestions:")
    for i, q in enumerate(quiz.questions, 1):
        print(f"\n{i}. {q.question}")
        for j, opt in enumerate(q.options, 1):
            print(f"   {j}) {opt}")
        print(f"   Correct: {q.correct_answer}")
        print(f"   Explanation: {q.explanation}")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("LangChain Service Usage Examples")
    print("=" * 60)
    
    try:
        await example_basic_usage()
        await example_structured_output()
        # await example_with_tools()  # Uncomment if tools are needed
        await example_with_context()
        await example_multiple_backends()
        await example_complex_structured_output()
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure GEMINI_API_KEY is set in your .env file")


if __name__ == "__main__":
    asyncio.run(main())
