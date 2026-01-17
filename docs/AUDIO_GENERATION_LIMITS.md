# Audio Generation Service - Content Limits

## Overview

The Gemini TTS (Text-to-Speech) API has specific limits on the amount of text that can be converted to audio in a single request. This document outlines these limits and how our service handles them.

## Official Limits

According to Google's documentation and community testing:

- **Maximum bytes per request**: 5,000 bytes
- **Maximum combined fields** (Vertex AI): 8,000 bytes (text + prompt)
- **Context window**: 32,000 tokens per TTS session
- **Maximum audio duration**: ~10-11 minutes

## Practical Limits (Implemented in Our Service)

Based on extensive testing and community feedback, we've implemented the following limits:

### Safe Limits (Recommended)
- **Words**: 500 words
- **Characters**: 2,500 characters
- **Bytes**: ~2,500 bytes

### Absolute Limits (Maximum)
- **Words**: 750 words
- **Characters**: 3,750 characters
- **Bytes**: 5,000 bytes (API hard limit)

## Why These Limits?

1. **Truncation Prevention**: Content exceeding these limits may be silently truncated (e.g., only first 750 words are converted)
2. **API Reliability**: Staying within safe limits ensures consistent, reliable audio generation
3. **Quality**: Shorter segments produce better quality audio with more natural pacing
4. **Error Prevention**: Prevents API errors and wasted quota on failed requests

## Implementation

### Audio Generation Service

The `AudioGenerationService` includes:

1. **Content Validation**: `validate_content_length()` method
2. **Automatic Checking**: Validation runs by default on all generation requests
3. **Custom Exception**: `ContentTooLongError` with detailed error messages
4. **Bypass Option**: Can disable validation with `validate=False` if needed

```python
from app.services.audio_generation_service import audio_generation_service, ContentTooLongError

# Automatic validation (recommended)
try:
    audio_bytes = await audio_generation_service.generate_audio_mp3(text=my_text)
except ContentTooLongError as e:
    print(f"Content too long: {e}")
    # Handle by chunking or truncating content

# Manual validation
try:
    audio_generation_service.validate_content_length(my_text, strict=True)
except ContentTooLongError as e:
    print(f"Content exceeds safe limits: {e}")

# Bypass validation (use with caution)
audio_bytes = await audio_generation_service.generate_audio_mp3(
    text=my_text, 
    validate=False
)
```

### Lecture Conversion Service

The `LectureConversionService` has been updated to:

1. **Enforce Word Limits**: AI is instructed to keep output between 400-450 words
2. **Prioritize Quality**: Focus on core concepts rather than covering everything
3. **Monitor Output**: Logs word count and warns if exceeding 500 words
4. **Automatic Compliance**: Ensures generated lecture scripts are TTS-safe

```python
from app.features.lessons.lecture_service import lecture_conversion_service

# Automatically generates script within safe limits (400-450 words)
lecture_script = await lecture_conversion_service.convert_to_lecture(lesson_content)
# Output will be validated when passed to audio generation
```

## Error Messages

When content exceeds limits, you'll receive a detailed error message:

```
Content too long for Gemini TTS:
  - Word count (850) exceeds absolute limit of 750 words
  - Character count (4249) exceeds absolute limit of 3750 characters

Current: 850 words, 4249 chars, 4249 bytes
Recommended: Split content into chunks of ~500 words or less
```

## Best Practices

### 1. Keep Content Concise
- Target 400-450 words for lecture scripts
- Focus on core concepts
- Use clear, conversational language

### 2. Chunk Long Content
If you have content exceeding 500 words:

```python
def chunk_text(text: str, max_words: int = 450) -> list[str]:
    """Split text into chunks of approximately max_words."""
    words = text.split()
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= max_words:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

# Generate audio for each chunk
for i, chunk in enumerate(chunk_text(long_content)):
    audio_bytes = await audio_generation_service.generate_audio_mp3(chunk)
    # Save or concatenate audio files
```

### 3. Monitor Word Counts
The lecture service automatically logs word counts:

```
Generated lecture script: 437 words
```

If you see warnings:
```
⚠️  Warning: Lecture script (523 words) exceeds safe limit of 500 words
```

Consider refining your content generation prompts.

### 4. Multi-byte Characters
Be aware that some characters (emoji, CJK characters, etc.) use multiple bytes:

- 1 emoji (🎉) = ~4 bytes
- 1 English word = ~5 bytes average
- 1 Chinese character = ~3 bytes

The byte limit (5,000) may be reached before the word limit with multi-byte content.

## Testing

Run the validation test suite:

```bash
source venv/bin/activate
python scripts/test_content_validation.py
```

This tests:
- ✅ Valid short content
- ✅ Content at safe limits
- ✅ Content exceeding safe limits (strict mode)
- ✅ Content at absolute limits
- ✅ Content exceeding absolute limits
- ✅ Multi-byte character handling
- ✅ Integration with audio generation

## Constants Reference

All limits are defined in `app/services/audio_generation_service.py`:

```python
MAX_BYTES_LIMIT = 5000          # Official API limit
MAX_WORDS_SAFE = 500            # Safe limit to avoid truncation
MAX_WORDS_ABSOLUTE = 750        # Absolute maximum observed
MAX_CHARACTERS_SAFE = 2500      # Safe character limit (~500 words)
MAX_CHARACTERS_ABSOLUTE = 3750  # Absolute maximum (~750 words)
```

## Related Files

- `app/services/audio_generation_service.py` - Audio generation with validation
- `app/features/lessons/lecture_service.py` - Lecture script generation with word limits
- `scripts/test_content_validation.py` - Validation test suite
- `scripts/test_audio_generation_and_upload.py` - End-to-end audio generation test

## References

- [Google AI Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [Vertex AI TTS Documentation](https://cloud.google.com/vertex-ai/docs)
- Community reports on Reddit and GitHub Issues

## Support

If you encounter issues with content limits:

1. Check word count: `len(text.split())`
2. Check byte size: `len(text.encode('utf-8'))`
3. Review error messages for specific violations
4. Consider chunking content if necessary
5. Adjust lecture generation prompts to produce shorter output
