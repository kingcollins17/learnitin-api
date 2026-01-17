"""Service for converting lesson content into a lecture script."""

from app.services.langchain_service import langchain_service


class LectureConversionService:
    """Service for converting lesson content into a lecture script."""

    def __init__(self):
        self.ai_service = langchain_service

    async def convert_to_lecture(self, lesson_content: str) -> str:
        """
        Convert lesson markdown content into a multi-speaker lecture script.

        Args:
            lesson_content: The markdown content of the lesson.

        Returns:
            A string formatted for text-to-speech with alternating speakers.
            The output is guaranteed to be within Gemini TTS limits (~500 words max).
        """
        system_prompt = """You are an expert educational scriptwriter.
Your task is to convert written lesson content into an engaging, natural-sounding audio lecture script for two speakers.
Speaker 1 (Female) is the main instructor: Knowledgeable, warm, clearer, and leads the lesson.
Speaker 2 (Male) is the co-host/student: Curious, asks clarifying questions, provides analogies, and summarizes key points.

Rules:
1. The output MUST be strictly formatted as:
Speaker 1: [Text]
Speaker 2: [Text]
...
2. Keep the tone conversational, engaging, and easy to follow.
3. Break down complex concepts into simple explanations.
4. Ensure the dialogue feels natural, like a podcast or radio show.
5. Cover the MOST IMPORTANT key points from the provided lesson content.
6. Do NOT use markdown formatting in the output, just plain text with Speaker labels.
7. Avoid long monologues; keep interactions dynamic.
8. **CRITICAL: The TOTAL output must be between 400-450 words maximum.** This is a hard limit for audio generation.
9. Prioritize quality over quantity - focus on the core concepts rather than trying to cover everything.
10. If the lesson content is very long, extract and explain only the most essential concepts.
"""

        user_prompt = """Convert the following lesson content into a lecture script:

{lesson_content}

Remember: Keep the output between 400-450 words total. Focus on the most important concepts.
"""

        lecture_script = await self.ai_service.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            lesson_content=lesson_content,
        )

        script_text = str(lecture_script)

        # Validate word count
        word_count = len(script_text.split())
        print(f"Generated lecture script: {word_count} words")

        # Warn if approaching limit (but don't fail - let audio service handle it)
        if word_count > 500:
            print(
                f"⚠️  Warning: Lecture script ({word_count} words) exceeds safe limit of 500 words"
            )

        return script_text


# Singleton instance
lecture_conversion_service = LectureConversionService()
