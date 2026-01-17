"""Service for converting audio formats using ffmpeg."""

import ffmpeg
import imageio_ffmpeg as iio


def pcm_to_mp3_bytes(
    pcm_bytes: bytes,
    sample_rate: int = 24000,  # Google TTS default sample rate
    channels: int = 1,  # Google TTS usually outputs mono
    bitrate: str = "128k",  # MP3 bitrate
) -> bytes:
    """
    Convert raw PCM bytes to MP3 bytes using ffmpeg-python in-memory.

    Uses imageio-ffmpeg's bundled FFmpeg binary, so no system FFmpeg installation required.
    This makes it work in restricted environments like Render.

    Args:
        pcm_bytes: Raw PCM audio data as bytes
        sample_rate: Audio sample rate in Hz (default: 24000)
        channels: Number of audio channels (default: 1 for mono)
        bitrate: MP3 output bitrate (default: "128k")

    Returns:
        MP3 encoded audio data as bytes

    Raises:
        RuntimeError: If ffmpeg conversion fails
    """
    # Get FFmpeg executable path from imageio-ffmpeg
    ffmpeg_path = iio.get_ffmpeg_exe()

    process = (
        ffmpeg.input(
            "pipe:0",  # read from stdin
            format="s16le",  # PCM signed 16-bit little endian
            ac=channels,
            ar=sample_rate,
        )
        .output(
            "pipe:1",  # output to stdout
            format="mp3",
            audio_bitrate=bitrate,
        )
        .run_async(
            pipe_stdin=True,
            pipe_stdout=True,
            pipe_stderr=True,
            cmd=ffmpeg_path,  # use the binary from imageio-ffmpeg
        )
    )

    mp3_bytes, err = process.communicate(input=pcm_bytes)

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {err.decode()}")

    return mp3_bytes
