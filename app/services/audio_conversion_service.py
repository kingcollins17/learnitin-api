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


def validate_audio_bytes(audio_bytes: bytes) -> bool:
    """
    Validate that the provided bytes are a valid MP3 file.
    Checks:
    1. Not empty
    2. Minimum size (e.g. > 100 bytes)
    3. FFmpeg can parse/decode the stream without errors.

    Args:
        audio_bytes: The audio data to validate.

    Returns:
        True if valid, False otherwise.
    """
    if (
        not audio_bytes or len(audio_bytes) < 100
    ):  # Minimum threshold for a valid MP3 header + some data
        return False

    ffmpeg_path = iio.get_ffmpeg_exe()

    try:
        # Run ffmpeg to decode the input to null, if it fails then the file is likely corrupted
        # -f null - is the standard way to test decoding without outputting anything
        process = (
            ffmpeg.input("pipe:0")
            .output("-", format="null")
            .run_async(
                pipe_stdin=True,
                pipe_stdout=True,
                pipe_stderr=True,
                cmd=ffmpeg_path,
            )
        )

        _, err = process.communicate(input=audio_bytes)

        if process.returncode != 0:
            print(
                f"Audio validation failed (ffmpeg exit code {process.returncode}): {err.decode()}"
            )
            return False

        return True
    except Exception as e:
        print(f"Error during audio validation: {e}")
        return False
