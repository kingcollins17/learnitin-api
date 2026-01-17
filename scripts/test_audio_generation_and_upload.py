import asyncio
import os
import sys

# Ensure the app module can be found
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from app.services.audio_generation_service import audio_generation_service
from app.services.storage_service import firebase_storage_service


async def test_mp3_generation_and_upload():
    """Test MP3 audio generation and upload to Firebase Storage."""
    print("\n" + "=" * 60)
    print("TEST: MP3 Audio Generation and Upload")
    print("=" * 60)

    # Test text with multi-speaker markup
    text = """
Read aloud in a warm, welcoming tone
Speaker 1: Hello! We're excited to show you our native speech capabilities.
Speaker 2: Where you can direct a voice, create realistic dialog, and so much more.
Speaker 1: This audio will be generated as MP3 and uploaded to Firebase Storage.
"""

    local_filename = "test_audio_output.mp3"

    try:
        # Step 1: Generate MP3 audio
        print("\n[Step 1/3] Generating MP3 audio...")
        mp3_bytes = await audio_generation_service.generate_audio_mp3(
            text=text, sample_rate=24000, bitrate="128k"
        )

        if not mp3_bytes:
            print("❌ Error: No audio data received from generation service.")
            return False

        print(f"✅ Generated {len(mp3_bytes)} bytes of MP3 data.")

        # Verify it's an MP3 file
        if mp3_bytes[:3] == b"ID3" or (
            mp3_bytes[0] == 0xFF and mp3_bytes[1] & 0xE0 == 0xE0
        ):
            print("✅ Valid MP3 file format detected")
        else:
            print("⚠️  Warning: File may not be a valid MP3")

        # Step 2: Save locally (optional, for verification)
        print(f"\n[Step 2/3] Saving MP3 locally to {local_filename}...")
        with open(local_filename, "wb") as f:
            f.write(mp3_bytes)
        print(f"✅ MP3 saved to: {os.path.abspath(local_filename)}")

        # Step 3: Upload to Firebase Storage
        print("\n[Step 3/3] Uploading MP3 to Firebase Storage...")
        folder_name = "test_audio_uploads"

        url = firebase_storage_service.upload_audio(
            audio_data=mp3_bytes, filename_prefix="test_generation", folder=folder_name
        )

        print(f"✅ Success! MP3 uploaded to Firebase Storage")
        print(f"📎 Public URL: {url}")

        return True

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_wav_generation():
    """Test WAV audio generation (optional)."""
    print("\n" + "=" * 60)
    print("TEST: WAV Audio Generation")
    print("=" * 60)

    text = """
Speaker 1: This is a test of WAV audio generation.
Speaker 2: WAV files are uncompressed and larger than MP3.
"""

    output_filename = "test_audio_output.wav"

    try:
        print("Generating WAV audio...")
        audio_bytes = await audio_generation_service.generate_audio(text)

        if not audio_bytes:
            print("❌ Error: No audio data received.")
            return False

        print(f"✅ Received {len(audio_bytes)} bytes of audio data.")

        # Verify it's a WAV file
        if audio_bytes[:4] == b"RIFF":
            print("✅ Valid WAV file format detected")
        else:
            print("⚠️  Warning: File may not be a valid WAV")

        with open(output_filename, "wb") as f:
            f.write(audio_bytes)

        print(f"✅ Success! Audio saved to: {os.path.abspath(output_filename)}")
        return True

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all audio generation and upload tests."""
    print("\n" + "=" * 60)
    print("AUDIO GENERATION & UPLOAD TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: MP3 generation and upload (primary test)
    mp3_upload_success = await test_mp3_generation_and_upload()
    results.append(("MP3 Generation & Upload", mp3_upload_success))

    # Test 2: WAV generation (optional, commented out by default)
    # wav_success = await test_wav_generation()
    # results.append(("WAV Generation", wav_success))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")

    all_passed = all(success for _, success in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
