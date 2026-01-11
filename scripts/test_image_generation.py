import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.image_generation_service import image_generation_service


async def main():
    print("Starting image generation test...")
    prompt = "A cute robot learning to code on a laptop in a futuristic city, digital art style"

    try:
        print(f"Generating image with prompt: '{prompt}'")
        image_bytes = await image_generation_service.generate_image(prompt)

        if image_bytes:
            output_filename = "test_image_output.png"
            output_path = os.path.join(os.getcwd(), output_filename)

            with open(output_path, "wb") as f:
                f.write(image_bytes)

            print(f"Success! Image saved to: {output_path}")
            print(f"Image size: {len(image_bytes)} bytes")
        else:
            print("Failed to generate image (returned None).")

    except Exception as e:
        print(f"Error generating image: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
