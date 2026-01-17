"""Service for converting lesson content into a lecture script."""

from typing import List
from pydantic import BaseModel
from app.services.langchain_service import langchain_service


class LectureScriptPart(BaseModel):
    """A single part of a broken-down lecture script."""

    title: str
    script: str
    order: int


class LectureConversionService:
    """Service for converting lesson content into a lecture script."""

    def __init__(self):
        self.ai_service = langchain_service

    async def convert_to_lecture(self, lesson_content: str) -> str:
        """
        Convert lesson markdown content into an in-depth multi-speaker lecture script.

        Args:
            lesson_content: The markdown content of the lesson.

        Returns:
            A comprehensive string formatted for text-to-speech with alternating speakers.
            This output is NOT constrained by word limits - it aims for depth and completeness.
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
5. Cover ALL key points from the provided lesson content thoroughly and in-depth.
6. Do NOT use markdown formatting in the output, just plain text with Speaker labels.
7. Avoid long monologues; keep interactions dynamic.
8. Be comprehensive - explain concepts fully with examples, analogies, and real-world applications.
9. Ensure smooth transitions between topics.
10. The script should feel complete and educational, like a full podcast episode.
11. **CRITICAL: The TOTAL output must be 1500 words maximum.** If the source content is extremely long, prioritize the most important concepts.
"""

        user_prompt = """Convert the following lesson content into a comprehensive lecture script:

{lesson_content}

Create an in-depth, thorough lecture that covers all the important concepts with clear explanations.
Remember: The total output must not exceed 1500 words.
"""

        lecture_script = await self.ai_service.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            lesson_content=lesson_content,
        )

        script_text = str(lecture_script)

        # Log word count for reference
        word_count = len(script_text.split())
        print(f"Generated lecture script: {word_count} words")

        return script_text

    async def generate_lecture_parts(
        self, lesson_content: str, max_parts: int = 10
    ) -> List[LectureScriptPart]:
        """
        Convert lesson content into lecture script parts ready for audio generation.

        This is the main entry point that combines lecture conversion and breakdown
        into a single operation. It generates an in-depth lecture script from the
        lesson content, then breaks it down into TTS-compatible parts.

        Args:
            lesson_content: The markdown content of the lesson.

        Returns:
            A list of LectureScriptPart objects, each containing:
            - title: Descriptive title for this part
            - script: The lecture script text (within TTS word limits)
            - order: The sequence number for this part
            max_parts: Maximum number of parts to generate (default: 10)
        """
        # Step 1: Convert lesson content to full lecture script
        full_script = await self.convert_to_lecture(lesson_content)

        # Step 2: Break down into TTS-compatible parts
        parts = await lecture_breakdown_service.breakdown_script(
            full_script, max_parts=max_parts
        )

        print(f"Generated {len(parts)} lecture parts for audio generation")

        return parts


class LectureBreakdownResponse(BaseModel):
    """Response schema for lecture breakdown."""

    parts: List[LectureScriptPart]


class LectureBreakdownService:
    """Service for breaking down a lecture script into TTS-compatible parts."""

    # Maximum words per part to stay within TTS limits
    MAX_WORDS_PER_PART = 450

    def __init__(self):
        self.ai_service = langchain_service

    async def breakdown_script(
        self, lecture_script: str, max_parts: int = 10
    ) -> List[LectureScriptPart]:
        """
        Break down a lecture script into multiple parts, each within TTS word limits.

        Args:
            lecture_script: The full lecture script text.
            max_parts: Maximum number of parts allowed.

        Returns:
            A list of LectureScriptPart objects, each containing a portion of the script
            that is within the word limit for text-to-speech generation.
        """
        word_count = len(lecture_script.split())

        # If script is already within limits, return as single part
        if word_count <= self.MAX_WORDS_PER_PART:
            return [
                LectureScriptPart(
                    title="Part 1",
                    script=lecture_script,
                    order=1,
                )
            ]

        # Use AI to intelligently break down the script with structured output
        system_prompt = """You are an expert at segmenting lecture scripts for audio production.
Your task is to break down a long lecture script into multiple parts, where each part:
1. Is a complete, self-contained segment of ~400-450 words maximum
2. Ends at a natural break point (end of a topic, transitional moment)
3. Maintains the Speaker 1:/Speaker 2: format throughout
4. Has a descriptive title summarizing that part's content

Rules:
1. Each part should be between 350-450 words to stay within TTS limits.
2. Never cut off mid-sentence or mid-thought.
3. Ensure each part can stand alone as a coherent segment.
4. Maintain speaker continuity - a part should ideally start with Speaker 1.
5. Create smooth transitions between parts where possible.
6. Assign order numbers starting from 1.
7. **CRITICAL: Do NOT generate more than {max_parts} parts.** If the script is too long to fit into {max_parts} parts of 450 words each (~{total_available_words} words total), you MUST shorten the content by picking only the most essential segments or summarizing less important parts to fit within the limit.
"""

        user_prompt = """Break down the following lecture script into multiple parts of ~400-450 words each.
        Remember, you are limited to a maximum of {max_parts} parts. Shorten or summarize if necessary.

        Lecture Script:
        {lecture_script}

        Return a structured list of parts with title, script content, and order number.
        """

        breakdown_response: LectureBreakdownResponse = await self.ai_service.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=LectureBreakdownResponse,
            lecture_script=lecture_script,
            max_parts=max_parts,
            total_available_words=max_parts * self.MAX_WORDS_PER_PART,
        )  # ty:ignore[invalid-assignment]

        # Validate and adjust if needed
        validated_parts = self._validate_parts(breakdown_response.parts)

        return validated_parts

    def _validate_parts(
        self, parts: List[LectureScriptPart]
    ) -> List[LectureScriptPart]:
        """Validate that all parts are within word limits, splitting if necessary."""
        validated = []
        order = 1

        for part in parts:
            word_count = len(part.script.split())

            if word_count <= self.MAX_WORDS_PER_PART:
                validated.append(
                    LectureScriptPart(
                        title=part.title,
                        script=part.script,
                        order=order,
                    )
                )
                order += 1
            else:
                # Part is still too long, do a simple split
                sub_parts = self._simple_split(part.script, part.title)
                for sub_part in sub_parts:
                    validated.append(
                        LectureScriptPart(
                            title=sub_part.title,
                            script=sub_part.script,
                            order=order,
                        )
                    )
                    order += 1

        return validated

    def _simple_split(self, script: str, base_title: str) -> List[LectureScriptPart]:
        """Perform a simple word-based split as a fallback."""
        words = script.split()
        parts = []
        current_words = []
        part_num = 1

        for word in words:
            current_words.append(word)
            if len(current_words) >= self.MAX_WORDS_PER_PART:
                # Try to find a natural break point (end of speaker line)
                text = " ".join(current_words)
                last_speaker_break = max(
                    text.rfind("\nSpeaker 1:"),
                    text.rfind("\nSpeaker 2:"),
                )
                if last_speaker_break > len(text) // 2:
                    # Found a good break point
                    parts.append(
                        LectureScriptPart(
                            title=f"{base_title} - Part {part_num}",
                            script=text[:last_speaker_break].strip(),
                            order=part_num,
                        )
                    )
                    current_words = text[last_speaker_break:].split()
                else:
                    # No good break point, just split at limit
                    parts.append(
                        LectureScriptPart(
                            title=f"{base_title} - Part {part_num}",
                            script=text.strip(),
                            order=part_num,
                        )
                    )
                    current_words = []
                part_num += 1

        # Add remaining words
        if current_words:
            parts.append(
                LectureScriptPart(
                    title=f"{base_title} - Part {part_num}",
                    script=" ".join(current_words).strip(),
                    order=part_num,
                )
            )

        return parts


# Singleton instances
lecture_conversion_service = LectureConversionService()
lecture_breakdown_service = LectureBreakdownService()
