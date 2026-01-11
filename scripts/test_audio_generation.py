import asyncio
import os
import sys

# Ensure the app module can be found
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from app.services.audio_generation_service import audio_generation_service


async def main():
    print("Starting audio generation test...")

    # Example text with multi-speaker markup (shortened for test)
    text = """
Read aloud in a warm, welcoming tone
Speaker 1: Hello! We're excited to show you our native speech capabilities
Speaker 2: Where you can direct a voice, create realistic dialog, and so much more. Edit these placeholders to get started.
"""

    output_filename = "test_audio_output.wav"

    try:
        print("Sending request to Gemini...")
        audio_bytes = await audio_generation_service.generate_audio(text)

        if not audio_bytes:
            print("Error: No audio data received.")
            return

        print(f"Received {len(audio_bytes)} bytes of audio data.")

        with open(output_filename, "wb") as f:
            f.write(audio_bytes)

        print(f"Success! Audio saved to: {os.path.abspath(output_filename)}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
