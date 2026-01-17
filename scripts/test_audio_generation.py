import asyncio
import os
import sys

# Ensure the app module can be found
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from app.services.audio_generation_service import audio_generation_service


async def test_wav_generation():
    """Test WAV audio generation."""
    print("\n" + "=" * 60)
    print("TEST 1: WAV Audio Generation")
    print("=" * 60)

    # Example text with multi-speaker markup (shortened for test)
    text = """
Read aloud in a warm, welcoming tone
Speaker 1: Hello! We're excited to show you our native speech capabilities
Speaker 2: Where you can direct a voice, create realistic dialog, and so much more. Edit these placeholders to get started.
"""

    output_filename = "test_audio_output.wav"

    try:
        print("Sending request to Gemini for WAV audio...")
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


async def test_mp3_generation():
    """Test MP3 audio generation."""
    print("\n" + "=" * 60)
    print("TEST 2: MP3 Audio Generation")
    print("=" * 60)

    # Shorter text for MP3 test
    text = """
Speaker 1: This is a test of the MP3 audio conversion service.
Speaker 2: The audio should be encoded in MP3 format with 128k bitrate.
"""

    output_filename = "test_audio_output.mp3"

    try:
        print("Sending request to Gemini for MP3 audio...")
        mp3_bytes = await audio_generation_service.generate_audio_mp3(
            text=text, sample_rate=24000, bitrate="128k"
        )

        if not mp3_bytes:
            print("❌ Error: No audio data received.")
            return False

        print(f"✅ Received {len(mp3_bytes)} bytes of MP3 data.")

        # Verify it's an MP3 file
        # MP3 files typically start with ID3 tag or sync word (0xFF 0xFB/0xFA)
        if mp3_bytes[:3] == b"ID3" or (
            mp3_bytes[0] == 0xFF and mp3_bytes[1] & 0xE0 == 0xE0
        ):
            print("✅ Valid MP3 file format detected")
        else:
            print("⚠️  Warning: File may not be a valid MP3")

        with open(output_filename, "wb") as f:
            f.write(mp3_bytes)

        print(f"✅ Success! MP3 audio saved to: {os.path.abspath(output_filename)}")
        return True

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all audio generation tests."""
    print("\n" + "=" * 60)
    print("AUDIO GENERATION TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: WAV generation
    # wav_success = await test_wav_generation()
    # results.append(("WAV Generation", wav_success))

    # Test 2: MP3 generation
    mp3_success = await test_mp3_generation()
    results.append(("MP3 Generation", mp3_success))

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
