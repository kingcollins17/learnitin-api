"""Service for uploading files to Firebase Storage."""

import os
import uuid
import json
from typing import Optional
import datetime

import firebase_admin
from firebase_admin import credentials, storage

from app.common.config import settings


class FirebaseStorageService:
    """Service for interacting with Firebase Storage."""

    def __init__(self):
        self.bucket_name = settings.FIREBASE_STORAGE_BUCKET
        self._initialize_app()

    def _initialize_app(self):
        """Initialize Firebase Admin SDK if not already initialized."""
        if not firebase_admin._apps:
            cred = None
            if settings.FIREBASE_CREDENTIALS_JSON:
                try:
                    # If it's a path to a file
                    if os.path.exists(settings.FIREBASE_CREDENTIALS_JSON):
                        cred = credentials.Certificate(
                            settings.FIREBASE_CREDENTIALS_JSON
                        )
                    else:
                        # Try parsing as JSON string
                        cred_info = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                        cred = credentials.Certificate(cred_info)
                except Exception as e:
                    print(f"Error loading Firebase credentials: {e}")

            # If no explicit creds, let it try default (e.g. GCLOUD)
            # or if cred was successfully created
            if cred:
                firebase_admin.initialize_app(cred, {"storageBucket": self.bucket_name})
            else:
                # Fallback to default or assume already configured
                # If bucket_name is provided, use it
                options = {}
                if self.bucket_name:
                    options["storageBucket"] = self.bucket_name

                try:
                    firebase_admin.initialize_app(options=options)
                except ValueError:
                    # App might be already initialized differently
                    pass

    def upload_bytes(
        self,
        data: bytes,
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Uploads bytes to Firebase Storage and returns the public URL.

        Args:
            data: The bytes to upload.
            destination_path: The path in the bucket (e.g., 'images/pic.jpg').
            content_type: The MIME type of the file.

        Returns:
            The public download URL of the uploaded file.
        """
        bucket = storage.bucket()
        blob = bucket.blob(destination_path)

        blob.upload_from_string(data, content_type=content_type)

        # Make the blob public. This typically requires the bucket to allow it
        # or specific IAM permissions.
        # Alternatively we can generte a long-lived signed URL.
        # But 'internet downloadable url' usually implies a direct link.

        # Method 1: Signed URL (safer default if public access config is unknown)
        # url = blob.generate_signed_url(expiration=datetime.timedelta(days=3650), method='GET')

        # Method 2: Public URL (requires blob.make_public())
        blob.make_public()
        return blob.public_url

    def upload_audio(
        self,
        audio_data: bytes,
        filename_prefix: str = "audio",
        folder: str = "generated_audio",
    ) -> str:
        """
        Helper to upload audio data specifically.

        Auto-detects audio format (WAV or MP3) based on file headers.

        Args:
            audio_data: Bytes of the audio file (WAV or MP3).
            filename_prefix: Prefix for the filename.
            folder: The subfolder to save the file in.

        Returns:
            Public URL.
        """
        # Detect audio format based on file header
        if len(audio_data) >= 4:
            # Check for WAV (RIFF header)
            if audio_data[:4] == b"RIFF":
                extension = "wav"
                content_type = "audio/wav"
            # Check for MP3 (ID3 tag or sync word)
            elif audio_data[:3] == b"ID3" or (
                audio_data[0] == 0xFF and audio_data[1] & 0xE0 == 0xE0
            ):
                extension = "mp3"
                content_type = "audio/mpeg"
            else:
                # Default to WAV if unknown
                extension = "wav"
                content_type = "audio/wav"
        else:
            # Default to WAV for very small files
            extension = "wav"
            content_type = "audio/wav"

        filename = f"{filename_prefix}_{uuid.uuid4()}.{extension}"
        # Ensure proper path formation without double slashes if folder is empty
        if folder:
            destination = f"{folder}/{filename}"
        else:
            destination = filename

        return self.upload_bytes(audio_data, destination, content_type)


# Singleton instance
firebase_storage_service = FirebaseStorageService()
