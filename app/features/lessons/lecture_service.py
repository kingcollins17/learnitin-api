"""Service for converting lesson content into a lecture script."""

from typing import List, cast
from pydantic import BaseModel
from app.services.langchain_service import LangChainService


class LectureScriptPart(BaseModel):
    """A single part of a broken-down lecture script."""

    title: str
    script: str
    order: int


class LectureConversionService:
    """Service for converting lesson content into a lecture script."""

    # Maximum words per part to stay within TTS limits
    MAX_WORDS_PER_PART = 450

    def __init__(self, ai_service: LangChainService):
        self.ai_service = ai_service

    async def generate_lecture_parts(
        self, lesson_content: str, max_parts: int = 10, provider: str = "google"
    ) -> List[LectureScriptPart]:
        """
        Convert lesson content directly into structured lecture script parts ready for audio generation.

        This single-step operation converts the lesson content into a list of parts within
        TTS word limits, avoiding multiple LLM calls.

        Args:
            lesson_content: The markdown content of the lesson.
            max_parts: Maximum number of parts to generate (default: 10)
            provider: Audio TTS provider ("google" or "deepgram")

        Returns:
            A list of LectureScriptPart objects.
        """
        if provider.lower() == "deepgram":
            system_prompt = """You are an expert educational scriptwriter.
Your task is to take written lesson content and convert it directly into an engaging, natural-sounding audio monologue lecture script broken down into multiple self-contained parts (maximum {max_parts} parts).

Each part:
1. Is a complete, self-contained segment of ~350-450 words maximum (to stay within text-to-speech limits).
2. Ends at a natural break point (end of a topic, transitional moment).
3. Must be a single-speaker narrator script. Do NOT use speaker labels (e.g., Speaker 1:, Speaker 2:) or dialogue formatting. Just write a continuous, engaging monologue.
4. Has a descriptive title summarizing that part's content.

Rules:
1. Never cut off mid-sentence or mid-thought between parts.
2. Ensure each part can stand alone as a coherent segment.
3. Keep the tone conversational, engaging, like an audiobook or documentary narration.
4. Do NOT use markdown formatting in the script content.
5. Assign order numbers starting from 1.
6. **CRITICAL: Do NOT generate more than {max_parts} parts.** If the source content is extremely long, prioritize the most important concepts to fit within the limit.
"""
        else:
            system_prompt = """You are an expert educational scriptwriter.
Your task is to take written lesson content and convert it directly into an engaging, natural-sounding audio lecture script broken down into multiple self-contained dialogue parts (maximum {max_parts} parts).

Each part:
1. Is a complete, self-contained segment of ~350-450 words maximum (to stay within text-to-speech limits).
2. Ends at a natural break point (end of a topic, transitional moment).
3. Must be strictly formatted with alternating speakers:
   Speaker 1 (Female) is the main instructor: Knowledgeable, warm, clearer, and leads the lesson.
   Speaker 2 (Male) is the co-host/student: Curious, asks clarifying questions, provides analogies, and summarizes key points.
   The text for each part must use:
   Speaker 1: [Text]
   Speaker 2: [Text]
   ...
4. Has a descriptive title summarizing that part's content.

Rules:
1. Never cut off mid-sentence or mid-thought between parts.
2. Ensure each part can stand alone as a coherent segment.
3. Keep the tone conversational, engaging, like a podcast or radio show.
4. Do NOT use markdown formatting in the script content, just plain text with Speaker labels.
5. Assign order numbers starting from 1.
6. **CRITICAL: Do NOT generate more than {max_parts} parts.** If the source content is extremely long, prioritize the most essential concepts to fit within the limit.
"""

        user_prompt = """Convert the following lesson content directly into a structured list of lecture parts (maximum {max_parts} parts) of ~350-450 words each.

        Lesson Content:
        {lesson_content}

        Return a structured list of parts with title, script content, and order number.
        """

        response = cast(
            LectureBreakdownResponse,
            await self.ai_service.invoke(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=LectureBreakdownResponse,
                lesson_content=lesson_content,
                max_parts=max_parts,
            ),
        )

        parts = self._validate_parts(response.parts, provider=provider)
        print(f"Generated {len(parts)} lecture parts for audio generation ({provider})")

        return parts

    def _validate_parts(
        self, parts: List[LectureScriptPart], provider: str = "google"
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
                sub_parts = self._simple_split(part.script, part.title, provider=provider)
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

    def _simple_split(self, script: str, base_title: str, provider: str = "google") -> List[LectureScriptPart]:
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
                if provider.lower() != "deepgram":
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
                        part_num += 1
                        continue

                # No good break point or deepgram, just split at limit
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


class LectureBreakdownResponse(BaseModel):
    """Response schema for lecture breakdown."""

    parts: List[LectureScriptPart]
