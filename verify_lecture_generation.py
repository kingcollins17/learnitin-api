import asyncio
from app.common.config import settings
from app.services.langchain_service import LangChainService
from app.features.lessons.lecture_service import LectureConversionService

async def main():
    print("Initializing LangChainService and LectureConversionService...")
    ai_service = LangChainService(settings=settings, backend="gemini")
    lecture_service = LectureConversionService(ai_service=ai_service)

    sample_content = """
    # Introduction to Python Variables
    Variables are containers for storing data values. In Python, you create a variable by assigning a value to it:
    
    ```python
    x = 5
    y = "Hello, World!"
    ```
    
    Python has no command for declaring a variable; it is created the moment you first assign a value to it.
    """

    # Test Google (Dialogue)
    print("\n--- Testing Google (Dialogue) ---")
    try:
        parts = await lecture_service.generate_lecture_parts(sample_content, max_parts=2, provider="google")
        for p in parts:
            print(f"[{p.order}] {p.title}")
            print(p.script)
            print("-" * 40)
    except Exception as e:
        print(f"Google Dialogue generation failed: {e}")

    # Test Deepgram (Monologue)
    print("\n--- Testing Deepgram (Monologue) ---")
    try:
        parts = await lecture_service.generate_lecture_parts(sample_content, max_parts=2, provider="deepgram")
        for p in parts:
            print(f"[{p.order}] {p.title}")
            print(p.script)
            print("-" * 40)
    except Exception as e:
        print(f"Deepgram Monologue generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
