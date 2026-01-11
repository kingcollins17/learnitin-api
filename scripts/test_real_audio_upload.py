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
    print("Starting real audio upload test...")

    file_path = Path("test_audio_output.wav")
    if not file_path.exists():
        print(f"Error: File {file_path} not found. Run test_audio_generation.py first.")
        return

    print(f"Reading file: {file_path}")
    audio_bytes = file_path.read_bytes()
    print(f"File size: {len(audio_bytes)} bytes")

    try:
        folder_name = "generated_test_files"
        print(f"Uploading to folder: {folder_name}...")

        url = firebase_storage_service.upload_audio(
            audio_data=audio_bytes,
            filename_prefix="real_audio_test",
            folder=folder_name,
        )

        print(f"Success! File uploaded to: {url}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
