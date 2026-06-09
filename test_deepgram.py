# For more Python SDK migration guides, visit:
# https://github.com/deepgram/deepgram-python-sdk/tree/main/docs

import os

# Load DEEPGRAM_API_KEY from .env first before importing deepgram
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("DEEPGRAM_API_KEY="):
                val = line.strip().split("=", 1)[1].strip()
                # Remove quotes if present
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                os.environ["DEEPGRAM_API_KEY"] = val

from deepgram import (
    DeepgramClient,
)

def main():
    try:
        # STEP 1 Create a Deepgram client using the API key from environment variables
        api_key = os.environ.get("DEEPGRAM_API_KEY")
        deepgram = DeepgramClient(api_key=api_key)

        # STEP 2 Call the generate method on the speak property
        response = deepgram.speak.v1.audio.generate(
            text="Hello world!",
            model="aura-2-thalia-en"
        )

        # Save the audio file (the response is a generator of bytes chunks)
        with open("test.mp3", "wb") as audio_file:
            for chunk in response:
                audio_file.write(chunk)

        print(f"Audio saved to test.mp3")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    main()
