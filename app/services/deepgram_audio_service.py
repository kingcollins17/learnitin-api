"""Service for generating audio from text using Deepgram."""

import asyncio
from enum import Enum
from typing import Union
from deepgram import DeepgramClient
from app.common.config import Settings


class DeepgramVoice(str, Enum):
    """Available Deepgram Aura voice models for text-to-speech."""
    THALIA = "aura-2-thalia-en"
    ODYSSEUS = "aura-2-odysseus-en"
    ANDROMEDA = "aura-2-andromeda-en"


class DeepgramAudioService:
    """Service for generating audio content via Deepgram TTS."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = settings.DEEPGRAM_API_KEY
        if not self.api_key:
            print("Warning: DEEPGRAM_API_KEY not set")

    async def generate_audio(
        self, text: str, model: Union[DeepgramVoice, str] = DeepgramVoice.THALIA
    ) -> bytes:
        """
        Generates audio (MP3) from the given text asynchronously.

        Args:
            text: The text to convert to speech.
            model: The Deepgram voice model (Enum or string) to use.

        Returns:
            The generated audio data as bytes (MP3 format).
        """
        model_str = model.value if isinstance(model, DeepgramVoice) else model
        return await asyncio.get_event_loop().run_in_executor(
            None, self._generate_audio_sync, text, model_str
        )

    def _generate_audio_sync(self, text: str, model: str) -> bytes:
        """
        Synchronous implementation of Deepgram TTS generation.
        """
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY is not set")

        # Create a Deepgram client using the API key
        deepgram = DeepgramClient(api_key=self.api_key)

        # Call the generate method on the speak property
        response = deepgram.speak.v1.audio.generate(
            text=text,
            model=model
        )

        # Accumulate the bytes from the response generator
        combined_data = bytearray()
        for chunk in response:
            combined_data.extend(chunk)

        return bytes(combined_data)

