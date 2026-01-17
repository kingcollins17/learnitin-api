# Audio Conversion Service

## Overview

The `audio_conversion_service.py` module provides functionality for converting raw PCM audio data to MP3 format using ffmpeg-python with imageio-ffmpeg.

**Key Feature:** Uses `imageio-ffmpeg` which bundles a standalone FFmpeg binary, eliminating the need for system FFmpeg installation. This makes it perfect for restricted environments like Render, Heroku, or Docker containers.

## Installation

The required dependencies are already added to `requirements.txt`:

```bash
pip install ffmpeg-python imageio-ffmpeg
```

**No system FFmpeg installation required!** The `imageio-ffmpeg` package includes a pre-compiled FFmpeg binary that works out of the box.

## Usage

### Direct PCM to MP3 Conversion

```python
from app.services.audio_conversion_service import pcm_to_mp3_bytes

# Convert PCM bytes to MP3
pcm_data = b"..."  # Your raw PCM audio data
mp3_data = pcm_to_mp3_bytes(
    pcm_bytes=pcm_data,
    sample_rate=24000,  # Google TTS default
    channels=1,         # Mono audio
    bitrate="128k"      # MP3 bitrate
)

# Save to file
with open("output.mp3", "wb") as f:
    f.write(mp3_data)
```

### Using AudioGenerationService

The `AudioGenerationService` now includes methods for MP3 generation:

```python
from app.services.audio_generation_service import audio_generation_service

# Generate audio directly in MP3 format
text = "Hello, this is a test of the audio generation service."
mp3_audio = await audio_generation_service.generate_audio_mp3(
    text=text,
    sample_rate=24000,
    bitrate="128k"
)

# Or convert existing PCM to MP3
pcm_data = b"..."  # Your PCM data
mp3_data = audio_generation_service._convert_pcm_to_mp3(
    pcm_bytes=pcm_data,
    sample_rate=24000,
    channels=1,
    bitrate="128k"
)
```

## Parameters

### `pcm_to_mp3_bytes()`

- **pcm_bytes** (bytes): Raw PCM audio data in signed 16-bit little-endian format
- **sample_rate** (int, default=24000): Audio sample rate in Hz
- **channels** (int, default=1): Number of audio channels (1=mono, 2=stereo)
- **bitrate** (str, default="128k"): MP3 output bitrate (e.g., "128k", "192k", "320k")

**Returns:** MP3 encoded audio data as bytes

**Raises:** `RuntimeError` if ffmpeg conversion fails

## Testing

Run the test script to verify the conversion works:

```bash
python test_mp3_conversion.py
```

This will generate a test MP3 file and verify the conversion process.

## Technical Details

### Audio Format

- **Input Format**: PCM signed 16-bit little-endian (s16le)
- **Output Format**: MP3
- **Default Sample Rate**: 24000 Hz (Google TTS default)
- **Default Channels**: 1 (mono)
- **Default Bitrate**: 128k

### In-Memory Processing

The conversion is done entirely in-memory using pipes:
- Input: `pipe:0` (stdin)
- Output: `pipe:1` (stdout)

This avoids writing temporary files to disk, making the conversion faster and more efficient.

### FFmpeg Binary

The service uses `imageio-ffmpeg` which provides:
- **Bundled FFmpeg binary**: No system installation required
- **Cross-platform support**: Works on Linux, macOS, and Windows
- **Version**: FFmpeg 4.x (bundled with imageio-ffmpeg)
- **Perfect for cloud deployments**: Works in restricted environments like Render, Heroku, AWS Lambda, etc.

The FFmpeg executable path is automatically retrieved using `imageio_ffmpeg.get_ffmpeg_exe()`.

## Error Handling

The function will raise a `RuntimeError` if ffmpeg encounters an error during conversion. The error message will include the stderr output from ffmpeg for debugging.

```python
try:
    mp3_data = pcm_to_mp3_bytes(pcm_bytes)
except RuntimeError as e:
    print(f"Conversion failed: {e}")
```
