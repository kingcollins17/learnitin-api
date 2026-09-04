"""Service for uploading files to Firebase Storage or Cloudflare R2 Storage."""

from abc import ABC, abstractmethod
import os
import uuid
import json
import logging
from typing import Optional, BinaryIO
import datetime
import urllib.parse

import firebase_admin
from firebase_admin import credentials, storage

from app.common.config import Settings


logger = logging.getLogger(__name__)


class StorageService(ABC):
    """Abstract base class interface for storage services."""

    def get_env_path(self, path: str) -> str:
        """
        Prefixes destination path with current environment subfolder (e.g., 'production/', 'staging/').
        """
        clean_path = path.lstrip("/")
        env = (
            getattr(getattr(self, "settings", None), "ENVIRONMENT", None)
            or os.getenv("ENVIRONMENT")
            or os.getenv("ENV")
            or "staging"
        ).lower().strip()

        if env in ("production", "prod"):
            prefix = "production"
        elif env in ("staging", "stage"):
            prefix = "staging"
        elif env in ("development", "dev", "local"):
            prefix = "development"
        else:
            prefix = env

        if clean_path.startswith(f"{prefix}/"):
            return clean_path

        for known in ("production/", "staging/", "development/"):
            if clean_path.startswith(known):
                return clean_path

        return f"{prefix}/{clean_path}"

    @abstractmethod
    def upload_bytes(
        self,
        data: bytes,
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Uploads raw bytes to storage and returns the public or storage URL.

        Args:
            data: The bytes to upload.
            destination_path: The path in the bucket (e.g., 'images/pic.jpg').
            content_type: The MIME type of the file.

        Returns:
            The public download URL of the uploaded file.
        """
        pass

    @abstractmethod
    def upload(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Uploads a file-like object to storage and returns the public or storage URL.

        Args:
            file_obj: File-like object to upload.
            key: The path in the bucket.
            content_type: The MIME type of the file.

        Returns:
            The public download URL of the uploaded file.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def delete_file(self, file_url_or_key: str) -> bool:
        """
        Deletes a file from storage given its public URL or path key.

        Args:
            file_url_or_key: The public URL or path key of the file.

        Returns:
            True if deleted, False otherwise.
        """
        pass

    # @abstractmethod
    # def generate_presigned_url(
    #     self,
    #     action: str = "put_object",
    #     key: str = "",
    #     content_type: str = "application/octet-stream",
    #     expires_in: int = 3600,
    # ) -> str:
    #     """
    #     Generates a presigned URL for direct client upload or download.

    #     Args:
    #         action: Operation action ('put_object' or 'get_object').
    #         key: Path key in bucket.
    #         content_type: MIME content type for upload.
    #         expires_in: Expiration time in seconds.

    #     Returns:
    #         Presigned URL string.
    #     """
        pass


class FirebaseStorageService(StorageService):
    """Service for interacting with Firebase Storage."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.bucket_name = settings.FIREBASE_STORAGE_BUCKET
        self._initialize_app()

    def _initialize_app(self):
        """Initialize Firebase Admin SDK if not already initialized."""
        if not firebase_admin._apps:
            options = {"storageBucket": self.bucket_name} if self.bucket_name else {}

            # If explicit credentials provided in settings, use them
            if self.settings.FIREBASE_CREDENTIALS_JSON:
                try:
                    if os.path.exists(self.settings.FIREBASE_CREDENTIALS_JSON):
                        cred = credentials.Certificate(
                            self.settings.FIREBASE_CREDENTIALS_JSON
                        )
                    else:
                        raw_json = self.settings.FIREBASE_CREDENTIALS_JSON
                        try:
                            cred_info = json.loads(raw_json, strict=False)
                        except Exception:
                            cleaned = raw_json.replace('\n', '\\n').replace('\r', '\\r')
                            cred_info = json.loads(cleaned, strict=False)
                        
                        if isinstance(cred_info, dict) and "private_key" in cred_info:
                            cred_info["private_key"] = cred_info["private_key"].replace("\\n", "\n")

                        cred = credentials.Certificate(cred_info)

                    firebase_admin.initialize_app(cred, options)
                    return
                except Exception as e:
                    logger.error(f"Error loading explicit Firebase credentials: {e}")

            # Fallback: Initialize with Google Application Default Credentials
            # This works automatically on Cloud Run or locally if GOOGLE_APPLICATION_CREDENTIALS is set
            try:
                firebase_admin.initialize_app(options=options)
            except Exception as e:
                logger.error(f"Firebase default initialization fallback: {e}")

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
        destination_path = self.get_env_path(destination_path)
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

    def upload(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Uploads a file-like object to Firebase Storage and returns the public URL.

        Args:
            file_obj: File-like object to upload.
            key: The path in the bucket.
            content_type: The MIME type of the file.

        Returns:
            The public download URL of the uploaded file.
        """
        data = file_obj.read()
        return self.upload_bytes(data, key, content_type)

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

    def delete_file(self, file_url_or_key: str) -> bool:
        """
        Deletes a file from Firebase Storage given its public URL or path key.

        Args:
            file_url_or_key: The public URL or path key of the file.

        Returns:
            True if deleted, False otherwise.
        """
        try:
            # Extract path from URL (e.g. https://storage.googleapis.com/bucket/folder/file.mp3)
            # Public URL format is usually: https://storage.googleapis.com/{bucket}/{path}
            # Or: https://firebasestorage.googleapis.com/v0/b/{bucket}/o/{path}?alt=media

            bucket = storage.bucket()

            # Simple path extraction for storage.googleapis.com URLs
            if "storage.googleapis.com" in file_url_or_key:
                path = file_url_or_key.split(f"{self.bucket_name}/")[-1]
            # Extraction for firebasestorage.googleapis.com URLs
            elif "firebasestorage.googleapis.com" in file_url_or_key:
                path = file_url_or_key.split("/o/")[-1].split("?")[0]
                path = urllib.parse.unquote(path)
            else:
                # Fallback: try to see if it's just a path
                path = file_url_or_key

            blob = bucket.blob(path)
            if blob.exists():
                blob.delete()
                logger.info(f"Successfully deleted {path} from storage.")
                return True
            else:
                logger.info(f"File {path} does not exist in storage.")
                return True
        except Exception as e:
            logger.error(f"Error deleting file from storage: {e}")
            return False

    def generate_presigned_url(
        self,
        action: str = "put_object",
        key: str = "",
        content_type: str = "application/octet-stream",
        expires_in: int = 3600,
    ) -> str:
        """
        Generates a signed URL for direct upload or download in Firebase Storage.

        Args:
            action: Operation action ('put_object' or 'get_object').
            key: Path key in bucket.
            content_type: MIME content type for upload.
            expires_in: Expiration time in seconds.

        Returns:
            Signed URL string.
        """
        bucket = storage.bucket()
        key = self.get_env_path(key)
        blob = bucket.blob(key)
        method = "GET" if action == "get_object" else "PUT"
        return blob.generate_signed_url(
            expiration=datetime.timedelta(seconds=expires_in),
            method=method,
            content_type=content_type if method == "PUT" else None,
        )

import logging
import urllib.parse
import uuid
from typing import BinaryIO, Optional

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


class CloudFlareStorageService(StorageService):
    """
    Cloudflare R2 object storage service using the S3-compatible API.

    Supports:
    - Direct server-side uploads
    - File-like object uploads
    - Object deletion
    - Presigned GET/PUT URLs
    - Public/custom-domain URLs when configured
    - R2 jurisdiction-specific endpoints
    """

    def __init__(self, settings: Settings):
        self.settings = settings

        self.account_id = settings.R2_ACCOUNT_ID
        self.access_key_id = settings.R2_ACCESS_KEY_ID
        self.secret_access_key = settings.R2_SECRET_ACCESS_KEY
        self.bucket_name = settings.R2_BUCKET_NAME.rstrip('/')

        # "default", "eu", "us", or "fedramp"
        self.jurisdiction = getattr(
            settings,
            "R2_JURISDICTION",
            "default",
        )

        # Optional public/custom domain.
        #
        # Example:
        # https://storage.learnitin.com
        #
        # Do NOT use the S3 endpoint here.
        self.public_domain = (
            settings.R2_PUBLIC_DOMAIN.rstrip("/")
            if settings.R2_PUBLIC_DOMAIN
            else None
        )

        self._s3_client = None

    @property
    def endpoint_url(self) -> str:
        """
        Return the correct R2 S3 endpoint.

        Default:
            https://<ACCOUNT_ID>.r2.cloudflarestorage.com

        Jurisdictional:
            https://<ACCOUNT_ID>.<JURISDICTION>.r2.cloudflarestorage.com
        """

        if self.jurisdiction == "default":
            return (
                f"https://{self.account_id}"
                f".r2.cloudflarestorage.com"
            )

        return (
            f"https://{self.account_id}"
            f".{self.jurisdiction}"
            f".r2.cloudflarestorage.com"
        )

    @property
    def client(self):
        """Lazily initialize the boto3 S3 client for Cloudflare R2."""

        if self._s3_client is None:
            try:
                self._s3_client = boto3.client(
                    service_name="s3",
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name="auto",
                    config=Config(
                        signature_version="s3v4",
                        s3={"addressing_style": "path"},
                    ),
                )

                logger.info(
                    "Initialized Cloudflare R2 client "
                    f"for bucket '{self.bucket_name}'"
                )

            except Exception:
                logger.exception(
                    "Failed to initialize Cloudflare R2 client"
                )
                raise

        return self._s3_client

    # -------------------------------------------------------------------------
    # URL helpers
    # -------------------------------------------------------------------------

    def _public_url(self, key: str) -> Optional[str]:
        """
        Return a public URL if a public/custom domain has been configured.

        Otherwise returns None.

        The R2 S3 API endpoint should NOT be treated as a public URL.
        """

        if not self.public_domain:
            return None

        return f"{self.public_domain}/{key.lstrip('/')}"

    # -------------------------------------------------------------------------
    # Upload
    # -------------------------------------------------------------------------

    def upload_bytes(
        self,
        data: bytes,
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload raw bytes to R2.

        Returns:
            Public URL if R2_PUBLIC_DOMAIN is configured.
            Otherwise returns the object key.
        """

        destination_path = self.get_env_path(destination_path)
        key = destination_path.lstrip("/")

        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

        public_url = self._public_url(key)

        if public_url:
            return public_url

        # For private buckets, don't pretend the S3 endpoint is public.
        return key

    def upload(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload a file-like object directly to R2.

        Returns:
            Public URL if configured.
            Otherwise the object key.
        """

        key = self.get_env_path(key)
        clean_key = key.lstrip("/")

        self.client.upload_fileobj(
            file_obj,
            self.bucket_name,
            clean_key,
            ExtraArgs={
                "ContentType": content_type,
            },
        )

        public_url = self._public_url(clean_key)

        if public_url:
            return public_url

        return clean_key

    # -------------------------------------------------------------------------
    # Audio helper
    # -------------------------------------------------------------------------

    def upload_audio(
        self,
        audio_data: bytes,
        filename_prefix: str = "audio",
        folder: str = "generated_audio",
    ) -> str:
        """
        Detect WAV/MP3 audio and upload it to R2.
        """

        if len(audio_data) >= 4:

            # WAV / RIFF
            if audio_data[:4] == b"RIFF":
                extension = "wav"
                content_type = "audio/wav"

            # MP3 with ID3 header
            elif audio_data[:3] == b"ID3":
                extension = "mp3"
                content_type = "audio/mpeg"

            # MP3 frame sync
            elif (
                len(audio_data) >= 2
                and audio_data[0] == 0xFF
                and (audio_data[1] & 0xE0) == 0xE0
            ):
                extension = "mp3"
                content_type = "audio/mpeg"

            else:
                extension = "wav"
                content_type = "audio/wav"

        else:
            extension = "wav"
            content_type = "audio/wav"

        filename = (
            f"{filename_prefix}_{uuid.uuid4()}.{extension}"
        )

        destination = (
            f"{folder}/{filename}"
            if folder
            else filename
        )

        return self.upload_bytes(
            audio_data,
            destination,
            content_type,
        )

    # -------------------------------------------------------------------------
    # Delete
    # -------------------------------------------------------------------------

    def delete_file(
        self,
        file_url_or_key: str,
    ) -> bool:
        """
        Delete an R2 object using either:

        - object key
        - configured public URL
        - URL pointing to the R2 endpoint
        """

        try:
            key = self._extract_key(file_url_or_key)

            if not key:
                logger.warning(
                    "Could not determine R2 object key from: %s",
                    file_url_or_key,
                )
                return False

            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key,
            )

            logger.info(
                "Deleted '%s' from R2 bucket '%s'",
                key,
                self.bucket_name,
            )

            return True

        except Exception:
            logger.exception(
                "Error deleting file from Cloudflare R2"
            )
            return False

    def _extract_key(self, value: str) -> str:
        """
        Convert a public URL, S3 endpoint URL, or raw key
        into an R2 object key.
        """

        value = value.strip()

        # Already a key
        if not value.startswith(("http://", "https://")):
            return value.lstrip("/")

        parsed = urllib.parse.urlparse(value)

        path = parsed.path.lstrip("/")

        # Custom/public domain:
        #
        # https://storage.example.com/foo/bar.png
        #
        # The entire path is the key.
        if self.public_domain:
            public_parsed = urllib.parse.urlparse(
                self.public_domain
            )

            if (
                parsed.scheme == public_parsed.scheme
                and parsed.netloc == public_parsed.netloc
            ):
                return path

        # R2 S3 endpoint:
        #
        # https://ACCOUNT_ID.r2.cloudflarestorage.com/
        #
        # and jurisdictional equivalents.
        endpoint_host = urllib.parse.urlparse(
            self.endpoint_url
        ).netloc

        if parsed.netloc == endpoint_host:
            return path

        # Unknown URL: use path as fallback.
        return path

    # -------------------------------------------------------------------------
    # Presigned URLs
    # -------------------------------------------------------------------------

    def generate_presigned_url(
        self,
        action: str,
        key: str,
        content_type: Optional[str] = None,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a presigned URL.

        Supported actions:
            get_object
            put_object
            head_object
            delete_object

        For put_object, content_type can be specified to bind
        the upload to a particular Content-Type.
        """

        supported_actions = {
            "get_object",
            "put_object",
            "head_object",
            "delete_object",
        }

        if action not in supported_actions:
            raise ValueError(
                f"Unsupported presigned URL action: {action}. "
                f"Supported actions: {sorted(supported_actions)}"
            )

        if not key:
            raise ValueError("Object key cannot be empty.")

        if expires_in < 1 or expires_in > 604800:
            raise ValueError(
                "expires_in must be between 1 second and 7 days."
            )

        key = self.get_env_path(key)
        clean_key = key.lstrip("/")

        params = {
            "Bucket": self.bucket_name,
            "Key": clean_key,
        }

        if action == "put_object" and content_type:
            params["ContentType"] = content_type

        return self.client.generate_presigned_url(
            ClientMethod=action,
            Params=params,
            ExpiresIn=expires_in,
        )

    def generate_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 900,
    ) -> str:
        """
        Generate a presigned PUT URL for direct client uploads.
        """

        return self.generate_presigned_url(
            action="put_object",
            key=key,
            content_type=content_type,
            expires_in=expires_in,
        )

    def generate_download_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a presigned GET URL for private object downloads.
        """

        return self.generate_presigned_url(
            action="get_object",
            key=key,
            expires_in=expires_in,
        )

class GoogleDriveStorageService(StorageService):
    """
    Service for interacting with Google Drive via Google API Python Client.

    WARNING / LIMITATION:
    ---------------------
    This service cannot be used for uploading binary/media files (> 0 bytes) to personal
    Google Drive folders using standard Service Accounts.

    Reason:
    Google Drive API assigns file storage quota usage to the file creator. GCP Service Accounts
    are allocated 0 Bytes of personal Drive storage quota by default. Consequently, uploading
    any non-zero file content to a personal folder (even if shared with Editor access or public)
    fails with: `HttpError 403: "Service Accounts do not have storage quota."`

    Requirements to activate this service in the future:
    1. Must use a Google Workspace Shared Drive (Team Drive), where quota belongs to the Shared Drive.
    2. OR use Domain-Wide Delegation to impersonate a licensed Google Workspace user account.
    """

    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self, settings: Settings):
        self.settings = settings
        self.credentials_json = (
            settings.GOOGLE_DRIVE_CREDENTIALS_JSON or settings.FIREBASE_CREDENTIALS_JSON
        )
        self.folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
        self._drive_service = None

    @property
    def drive(self):
        """Lazy initialization of Google Drive service client."""
        if self._drive_service is None:
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build

                if self.credentials_json:
                    if os.path.exists(self.credentials_json):
                        creds = service_account.Credentials.from_service_account_file(
                            self.credentials_json, scopes=self.SCOPES
                        )
                    else:
                        cred_dict = json.loads(
                            self.credentials_json.replace('\n', '\\n')
                        )
                        creds = service_account.Credentials.from_service_account_info(
                            cred_dict, scopes=self.SCOPES
                        )
                else:
                    raise ValueError("No Google Drive credentials JSON configured")

                self._drive_service = build("drive", "v3", credentials=creds)
            except Exception as e:
                logger.error(f"Failed to initialize Google Drive service client: {e}")
                raise e
        return self._drive_service

    def upload(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Uploads a file-like object to Google Drive.

        Args:
            file_obj: File-like object to upload.
            key: Target filename or path in Drive.
            content_type: MIME type of the file.

        Returns:
            Direct view/download URL for the uploaded Google Drive file.
        """
        import io
        from googleapiclient.http import MediaIoBaseUpload

        key = self.get_env_path(key)
        filename = os.path.basename(key) if key else "uploaded_file"
        metadata = {"name": filename}
        if self.folder_id:
            metadata["parents"] = [self.folder_id]

        media = MediaIoBaseUpload(file_obj, mimetype=content_type, resumable=True)
        result = (
            self.drive.files()
            .create(
                body=metadata,
                media_body=media,
                fields="id,name,webViewLink,webContentLink",
                supportsAllDrives=True,
            )
            .execute()
        )
        file_id = result.get("id")

        # Optionally grant anyone-reader permission so the file URL is publicly accessible
        try:
            self.drive.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
                supportsAllDrives=True,
            ).execute()
        except Exception as e:
            logger.warning(f"Could not set public permission on Google Drive file {file_id}: {e}")

        return (
            result.get("webViewLink")
            or f"https://drive.google.com/uc?export=view&id={file_id}"
        )

    def upload_bytes(
        self,
        data: bytes,
        destination_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Uploads raw bytes to Google Drive.

        Args:
            data: Raw bytes to upload.
            destination_path: Path/filename in Drive.
            content_type: MIME type of the file.

        Returns:
            Direct view/download URL for the uploaded Google Drive file.
        """
        import io

        buffer = io.BytesIO(data)
        return self.upload(buffer, destination_path, content_type)

    def upload_audio(
        self,
        audio_data: bytes,
        filename_prefix: str = "audio",
        folder: str = "generated_audio",
    ) -> str:
        """
        Auto-detects audio format (WAV or MP3) and uploads to Google Drive.

        Args:
            audio_data: Bytes of audio file.
            filename_prefix: Prefix for filename.
            folder: Subfolder prefix name.

        Returns:
            Direct view/download URL.
        """
        if len(audio_data) >= 4:
            if audio_data[:4] == b"RIFF":
                extension = "wav"
                content_type = "audio/wav"
            elif audio_data[:3] == b"ID3" or (
                audio_data[0] == 0xFF and audio_data[1] & 0xE0 == 0xE0
            ):
                extension = "mp3"
                content_type = "audio/mpeg"
            else:
                extension = "wav"
                content_type = "audio/wav"
        else:
            extension = "wav"
            content_type = "audio/wav"

        filename = f"{filename_prefix}_{uuid.uuid4()}.{extension}"
        key = f"{folder}/{filename}" if folder else filename
        return self.upload_bytes(audio_data, key, content_type)

    def delete_file(self, file_url_or_key: str) -> bool:
        """
        Deletes a file from Google Drive by its file ID or URL.

        Args:
            file_url_or_key: File ID or URL containing id= parameter.

        Returns:
            True if deleted, False otherwise.
        """
        try:
            file_id = file_url_or_key
            if "id=" in file_url_or_key:
                file_id = file_url_or_key.split("id=")[-1].split("&")[0]
            elif "/d/" in file_url_or_key:
                file_id = file_url_or_key.split("/d/")[1].split("/")[0]

            self.drive.files().delete(fileId=file_id, supportsAllDrives=True).execute()
            logger.info(f"Successfully deleted file {file_id} from Google Drive.")
            return True
        except Exception as e:
            logger.error(f"Error deleting file from Google Drive: {e}")
            return False

    def generate_presigned_url(
        self,
        action: str = "put_object",
        key: str = "",
        content_type: str = "application/octet-stream",
        expires_in: int = 3600,
    ) -> str:
        """
        Generates a direct view URL for Google Drive file (or file upload placeholder URL).
        """
        file_id = key
        if "id=" in key:
            file_id = key.split("id=")[-1].split("&")[0]
        return f"https://drive.google.com/uc?export=view&id={file_id}"
