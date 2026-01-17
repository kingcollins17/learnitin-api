"""Test script for PCM to MP3 conversion."""

import asyncio
from app.services.audio_generation_service import audio_generation_service


async def test_mp3_conversion():
    """Test generating audio in MP3 format."""
    print("Testing MP3 audio generation...")

    text = "Hello, this is a test of the MP3 audio conversion service."

    try:
        # Generate MP3 audio
        mp3_data = await audio_generation_service.generate_audio_mp3(text)

        if mp3_data:
            # Save to file
            output_file = "test_audio_output.mp3"
            with open(output_file, "wb") as f:
                f.write(mp3_data)

            print(f"✓ Successfully generated MP3 audio ({len(mp3_data)} bytes)")
            print(f"✓ Saved to {output_file}")

            # Check if it's a valid MP3 file
            if mp3_data[:3] == b"ID3" or (
                mp3_data[0] == 0xFF and mp3_data[1] & 0xE0 == 0xE0
            ):
                print("✓ Valid MP3 file format detected")
            else:
                print("⚠ Warning: File may not be a valid MP3")

        else:
            print("✗ Failed to generate audio")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mp3_conversion())
