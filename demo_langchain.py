"""
Quick demo of the LangChain service.
Run this to verify the service works with your GEMINI_API_KEY.
"""
import asyncio
from pydantic import BaseModel, Field
from app.services.langchain_service import LangChainService


class QuickAnswer(BaseModel):
    """Simple answer with confidence."""
    answer: str = Field(description="The answer to the question")
    confidence: float = Field(description="Confidence score between 0 and 1")


async def demo():
    """Run a quick demo of the service."""
    print("=" * 60)
    print("LangChain Service Demo")
    print("=" * 60)
    
    # Initialize service with Gemini
    service = LangChainService(backend="gemini", temperature=0.7)
    print("\n✓ Service initialized with Gemini backend")
    
    # Test 1: Basic text generation
    print("\n1. Basic Text Generation:")
    print("-" * 40)
    response = await service.invoke(
        system_prompt="You are a helpful educational assistant for LearnItIn platform.",
        user_prompt="In one sentence, what is Python?"
    )
    print(f"Response: {response}")
    
    # Test 2: Structured output
    print("\n2. Structured Output:")
    print("-" * 40)
    answer: QuickAnswer = await service.invoke(
        system_prompt="You are a helpful assistant.",
        user_prompt="What is 2 + 2?",
        response_schema=QuickAnswer
    )
    print(f"Answer: {answer.answer}")
    print(f"Confidence: {answer.confidence}")
    
    # Test 3: With context
    print("\n3. Context-Based Response:")
    print("-" * 40)
    context = "The user is a complete beginner in programming."
    response = await service.invoke_with_context(
        system_prompt="You are a patient programming tutor.",
        user_prompt="What is a variable?",
        context=context
    )
    print(f"Response: {response}")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(demo())
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure GEMINI_API_KEY is set in your .env file")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
