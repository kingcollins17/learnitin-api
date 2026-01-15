"""Utilities for managing Google Cloud credentials."""

import os
import json
import tempfile
from app.common.config import settings


def setup_google_adc():
    """
    Set up Application Default Credentials (ADC) from settings.
    If FIREBASE_CREDENTIALS_JSON is a JSON string, it writes it to a temporary file
    and sets GOOGLE_APPLICATION_CREDENTIALS to that file path.
    """
    if (
        not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        and settings.FIREBASE_CREDENTIALS_JSON
    ):
        try:
            # If it's a path to a file
            if os.path.exists(settings.FIREBASE_CREDENTIALS_JSON):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(
                    settings.FIREBASE_CREDENTIALS_JSON
                )
                print(f"Using ADC file: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")
            else:
                # It might be a JSON string, write to a temp file
                try:
                    # Validate it's JSON
                    json.loads(settings.FIREBASE_CREDENTIALS_JSON)

                    tmp_dir = tempfile.gettempdir()
                    tmp_path = os.path.join(tmp_dir, "google_credentials.json")

                    # Always overwrite or ensure it exists if directory is shared
                    with open(tmp_path, "w") as f:
                        f.write(settings.FIREBASE_CREDENTIALS_JSON)

                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp_path
                    print(f"Set ADC from JSON string to: {tmp_path}")
                except (json.JSONDecodeError, TypeError):
                    # Not JSON, maybe it's just missing or invalid
                    pass
        except Exception as e:
            print(f"Error setting up ADC from FIREBASE_CREDENTIALS_JSON: {e}")
