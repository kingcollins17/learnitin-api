"""Service for generating audio from text using Gemini."""

import asyncio
import mimetypes
import struct
from typing import Optional

from google import genai
from google.genai import types

from app.common.config import settings
from app.services.audio_conversion_service import pcm_to_mp3_bytes


class AudioGenerationService:
    """Service for generating audio content."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            print("Warning: GEMINI_API_KEY not set")

    async def generate_audio(self, text: str) -> bytes:
        """
        Generates audio (WAV) from the given text.

        Args:
            text: The text to convert to speech.

        Returns:
            The generated audio data as bytes (WAV format).
        """
        return await asyncio.get_event_loop().run_in_executor(
            None, self._generate_audio_sync, text
        )

    def _generate_audio_sync(self, text: str) -> bytes:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set")

        model = "gemini-2.5-pro-preview-tts"

        try:
            client = genai.Client(api_key=self.api_key, vertexai=False)
            print("Using Google AI (API Key) backend for audio generation")
        except Exception as e:
            print(f"Google AI (API Key) initialization failed: {e}")
            return b""

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=text),
                ],
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=[
                "audio",
            ],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=[
                        types.SpeakerVoiceConfig(
                            speaker="Speaker 1",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name="Zephyr"
                                )
                            ),
                        ),
                        types.SpeakerVoiceConfig(
                            speaker="Speaker 2",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name="Puck"
                                )
                            ),
                        ),
                    ]
                ),
            ),
        )

        combined_data = bytearray()
        last_mime_type = None
        is_raw_pcm = False

        try:
            # Iterate through the stream and collect data
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                if (
                    chunk.candidates is None
                    or not chunk.candidates
                    or chunk.candidates[0].content is None
                    or chunk.candidates[0].content.parts is None
                    or not chunk.candidates[0].content.parts
                ):
                    continue

                part = chunk.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    inline_data = part.inline_data
                    current_mime_type = inline_data.mime_type

                    # Determine if this is raw PCM or something else based on mime
                    ext = mimetypes.guess_extension(current_mime_type)
                    if ext is None:
                        is_raw_pcm = True
                        last_mime_type = current_mime_type

                    combined_data.extend(inline_data.data)
        except Exception as e:
            print(f"Error during generate_content_stream: {e}")
            return b""

        if not combined_data:
            return b""

        # If it was raw PCM, we need to add the WAV header based on the mime type parameters
        if is_raw_pcm:
            print("Is raw pcm")
            return self._convert_to_wav(
                bytes(combined_data),
                last_mime_type or "audio/L16;rate=24000",
            )

        # Otherwise return the accumulated data (e.g. if it was mp3)
        print("Generated audio is mp3")
        return bytes(combined_data)

    def _convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """Generates a WAV file header for the given audio data and parameters."""
        parameters = self._parse_audio_mime_type(mime_type)
        bits_per_sample = parameters["bits_per_sample"] or 16
        sample_rate = parameters["rate"] or 24000
        num_channels = 1
        data_size = len(audio_data)
        bytes_per_sample = bits_per_sample // 8
        block_align = num_channels * bytes_per_sample
        byte_rate = sample_rate * block_align
        chunk_size = 36 + data_size

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",  # ChunkID
            chunk_size,  # ChunkSize
            b"WAVE",  # Format
            b"fmt ",  # Subchunk1ID
            16,  # Subchunk1Size (16 for PCM)
            1,  # AudioFormat (1 for PCM)
            num_channels,  # NumChannels
            sample_rate,  # SampleRate
            byte_rate,  # ByteRate
            block_align,  # BlockAlign
            bits_per_sample,  # BitsPerSample
            b"data",  # Subchunk2ID
            data_size,  # Subchunk2Size
        )
        return header + audio_data

    def _convert_pcm_to_mp3(
        self,
        pcm_bytes: bytes,
        sample_rate: int = 24000,
        channels: int = 1,
        bitrate: str = "128k",
    ) -> bytes:
        """
        Convert raw PCM bytes to MP3 format.

        Args:
            pcm_bytes: Raw PCM audio data
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels
            bitrate: MP3 output bitrate

        Returns:
            MP3 encoded audio data as bytes
        """
        return pcm_to_mp3_bytes(
            pcm_bytes=pcm_bytes,
            sample_rate=sample_rate,
            channels=channels,
            bitrate=bitrate,
        )

    async def generate_audio_mp3(
        self, text: str, sample_rate: int = 24000, bitrate: str = "128k"
    ) -> bytes:
        """
        Generates audio in MP3 format from the given text.

        Args:
            text: The text to convert to speech.
            sample_rate: Audio sample rate (default: 24000 Hz)
            bitrate: MP3 bitrate (default: "128k")

        Returns:
            The generated audio data as bytes (MP3 format).
        """
        # First generate the audio (which may be PCM or MP3)
        audio_data = await self.generate_audio(text)

        # Check if it's already MP3 by looking at the header
        # MP3 files typically start with ID3 tag or sync word (0xFF 0xFB/0xFA)
        if len(audio_data) > 3 and (
            audio_data[:3] == b"ID3"
            or (audio_data[0] == 0xFF and audio_data[1] & 0xE0 == 0xE0)
        ):
            # Already MP3
            return audio_data

        # If it's WAV, we need to extract the PCM data and convert
        if audio_data[:4] == b"RIFF":
            # Extract PCM data from WAV (skip 44-byte header)
            pcm_data = audio_data[44:]
            return self._convert_pcm_to_mp3(
                pcm_bytes=pcm_data,
                sample_rate=sample_rate,
                channels=1,
                bitrate=bitrate,
            )

        # If it's raw PCM (no header), convert directly
        return self._convert_pcm_to_mp3(
            pcm_bytes=audio_data,
            sample_rate=sample_rate,
            channels=1,
            bitrate=bitrate,
        )

    def _parse_audio_mime_type(self, mime_type: str) -> dict[str, Optional[int]]:
        """Parses bits per sample and rate from an audio MIME type string."""
        bits_per_sample = 16
        rate = 24000

        if not mime_type:
            return {"bits_per_sample": bits_per_sample, "rate": rate}

        parts = mime_type.split(";")
        for param in parts:
            param = param.strip()
            if param.lower().startswith("rate="):
                try:
                    rate_str = param.split("=", 1)[1]
                    rate = int(rate_str)
                except (ValueError, IndexError):
                    pass
            elif param.startswith("audio/L"):
                try:
                    rest = param.split("L", 1)[1]
                    bits_per_sample = int(rest)
                except (ValueError, IndexError):
                    pass

        return {"bits_per_sample": bits_per_sample, "rate": rate}


# Singleton instance
audio_generation_service = AudioGenerationService()
