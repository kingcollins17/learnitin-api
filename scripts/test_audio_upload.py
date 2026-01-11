import asyncio
import os
import sys

# Ensure the app module can be found
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from app.services.audio_generation_service import audio_generation_service


from app.services.storage_service import firebase_storage_service
import uuid


async def main():
    print("Starting audio upload test...")

    # Create dummy audio data (1kb of silence/noise)
    dummy_wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    audio_bytes = dummy_wav_header + b"\x00" * 1000

    try:
        folder_name = "test_custom_folder"
        print(f"Uploading to folder: {folder_name}...")

        url = firebase_storage_service.upload_audio(
            audio_data=audio_bytes, filename_prefix="test_upload", folder=folder_name
        )

        print(f"Success! File uploaded to: {url}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
