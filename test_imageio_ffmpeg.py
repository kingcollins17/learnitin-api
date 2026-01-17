"""Quick test to verify imageio-ffmpeg is working."""

import imageio_ffmpeg as iio

# Test that we can get the FFmpeg executable
ffmpeg_path = iio.get_ffmpeg_exe()
print(f"✅ FFmpeg executable found at: {ffmpeg_path}")

# Test that the executable exists and is accessible
import os

if os.path.exists(ffmpeg_path):
    print("✅ FFmpeg binary exists and is accessible")
else:
    print("❌ FFmpeg binary not found")

# Get FFmpeg version
import subprocess

try:
    result = subprocess.run(
        [ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5
    )
    version_line = result.stdout.split("\n")[0]
    print(f"✅ {version_line}")
except Exception as e:
    print(f"❌ Error getting FFmpeg version: {e}")

print("\n🎉 imageio-ffmpeg is ready to use!")
