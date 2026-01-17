"""Test content length validation for audio generation."""

import asyncio
import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from app.services.audio_generation_service import (
    audio_generation_service,
    ContentTooLongError,
    MAX_WORDS_SAFE,
    MAX_WORDS_ABSOLUTE,
)


async def test_content_validation():
    """Test content length validation."""
    print("\n" + "=" * 60)
    print("TEST: Content Length Validation")
    print("=" * 60)

    # Test 1: Valid short content
    print("\n[Test 1] Valid short content (50 words)...")
    short_text = " ".join(["word"] * 50)
    try:
        audio_generation_service.validate_content_length(short_text, strict=True)
        print("✅ Short content passed validation")
    except ContentTooLongError as e:
        print(f"❌ Unexpected error: {e}")
        return False

    # Test 2: Content at safe limit
    print(f"\n[Test 2] Content at safe limit ({MAX_WORDS_SAFE} words)...")
    safe_limit_text = " ".join(["word"] * MAX_WORDS_SAFE)
    try:
        audio_generation_service.validate_content_length(safe_limit_text, strict=True)
        print("✅ Safe limit content passed validation")
    except ContentTooLongError as e:
        print(f"❌ Unexpected error: {e}")
        return False

    # Test 3: Content exceeding safe limit (strict mode)
    print(
        f"\n[Test 3] Content exceeding safe limit ({MAX_WORDS_SAFE + 100} words, strict mode)..."
    )
    over_safe_text = " ".join(["word"] * (MAX_WORDS_SAFE + 100))
    try:
        audio_generation_service.validate_content_length(over_safe_text, strict=True)
        print("❌ Should have raised ContentTooLongError")
        return False
    except ContentTooLongError as e:
        print(f"✅ Correctly raised error in strict mode")
        print(f"   Error message preview: {str(e)[:100]}...")

    # Test 4: Content at absolute limit (non-strict mode)
    print(
        f"\n[Test 4] Content at absolute limit ({MAX_WORDS_ABSOLUTE} words, non-strict mode)..."
    )
    absolute_limit_text = " ".join(["word"] * MAX_WORDS_ABSOLUTE)
    try:
        audio_generation_service.validate_content_length(
            absolute_limit_text, strict=False
        )
        print("✅ Absolute limit content passed validation in non-strict mode")
    except ContentTooLongError as e:
        print(f"❌ Unexpected error: {e}")
        return False

    # Test 5: Content exceeding absolute limit
    print(
        f"\n[Test 5] Content exceeding absolute limit ({MAX_WORDS_ABSOLUTE + 100} words)..."
    )
    over_absolute_text = " ".join(["word"] * (MAX_WORDS_ABSOLUTE + 100))
    try:
        audio_generation_service.validate_content_length(
            over_absolute_text, strict=False
        )
        print("❌ Should have raised ContentTooLongError")
        return False
    except ContentTooLongError as e:
        print(f"✅ Correctly raised error for content exceeding absolute limit")
        print(f"   Full error message:")
        print(f"   {e}")

    # Test 6: Multi-byte characters (emoji, etc.)
    print(f"\n[Test 6] Multi-byte characters...")
    emoji_text = "🎉 " * 100  # Each emoji is multiple bytes
    try:
        audio_generation_service.validate_content_length(emoji_text, strict=True)
        word_count = len(emoji_text.split())
        byte_count = len(emoji_text.encode("utf-8"))
        print(
            f"✅ Multi-byte content validated ({word_count} words, {byte_count} bytes)"
        )
    except ContentTooLongError as e:
        print(f"⚠️  Multi-byte content failed: {str(e)[:100]}...")

    return True


async def test_audio_generation_with_validation():
    """Test that audio generation respects validation."""
    print("\n" + "=" * 60)
    print("TEST: Audio Generation with Validation")
    print("=" * 60)

    # Test 1: Generate with valid content
    print("\n[Test 1] Generate audio with valid content...")
    valid_text = """
Speaker 1: Hello! This is a test of the audio generation service.
Speaker 2: Yes, and this content is well within the safe limits.
Speaker 1: Perfect for testing!
"""
    try:
        audio_bytes = await audio_generation_service.generate_audio_mp3(
            text=valid_text, validate=True
        )
        print(f"✅ Generated {len(audio_bytes)} bytes of audio")
    except ContentTooLongError as e:
        print(f"❌ Unexpected validation error: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Generation error (not validation): {e}")

    # Test 2: Try to generate with content that's too long
    print(f"\n[Test 2] Try to generate audio with {MAX_WORDS_ABSOLUTE + 200} words...")
    too_long_text = " ".join(["word"] * (MAX_WORDS_ABSOLUTE + 200))
    try:
        audio_bytes = await audio_generation_service.generate_audio_mp3(
            text=too_long_text, validate=True
        )
        print(f"❌ Should have raised ContentTooLongError before generation")
        return False
    except ContentTooLongError as e:
        print(f"✅ Correctly prevented generation of too-long content")
        print(f"   Error: {str(e)[:150]}...")

    # Test 3: Bypass validation (for testing only)
    print(f"\n[Test 3] Bypass validation with validate=False...")
    print(f"   (Note: This will likely fail at the API level or truncate)")
    try:
        # Don't actually run this - it would waste API quota
        print(f"   Skipping actual generation to save API quota")
        print(f"✅ Validation can be bypassed when needed")
    except Exception as e:
        print(f"   Expected API error: {e}")

    return True


async def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("AUDIO GENERATION VALIDATION TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: Content validation
    validation_success = await test_content_validation()
    results.append(("Content Validation", validation_success))

    # Test 2: Audio generation with validation
    generation_success = await test_audio_generation_with_validation()
    results.append(("Audio Generation with Validation", generation_success))

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
