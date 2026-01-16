"""Service for generating images using Gemini."""

import asyncio
from typing import Optional

from google import genai
from google.genai import types

from app.common.config import settings


class ImageGenerationService:
    """Service for generating image content."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            print("Warning: GEMINI_API_KEY not set")

    async def generate_image(self, prompt: str) -> Optional[bytes]:
        """
        Generates an image from the given text prompt.

        Args:
            prompt: The text prompt for image generation.

        Returns:
            The generated image data as bytes, or None if generation fails.
        """
        return await asyncio.get_event_loop().run_in_executor(
            None, self._generate_image_sync, prompt
        )

    def _generate_image_sync(self, prompt: str) -> Optional[bytes]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set")

        model = "gemini-3-pro-image-preview"

        try:
            client = genai.Client(api_key=self.api_key, vertexai=False)
            print("Using Google AI (API Key) backend for image generation")
        except Exception as e:
            print(f"Google AI (API Key) initialization failed: {e}")
            return None

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            response_modalities=[
                "IMAGE",
                "TEXT",
            ],
            image_config=types.ImageConfig(
                image_size="1K",
            ),
        )

        try:
            # Iterate through the stream and capture the first image found
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=generate_content_config,
            )

            if (
                response.candidates is None
                or not response.candidates
                or response.candidates[0].content is None
                or response.candidates[0].content.parts is None
                or not response.candidates[0].content.parts
            ):
                return None

            part = response.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                return part.inline_data.data

            if hasattr(part, "text") and part.text:
                print(f"Image generation text response: {part.text}")

        except Exception as e:
            print(f"Error during generate_content: {e}")

        return None


# Singleton instance
image_generation_service = ImageGenerationService()
