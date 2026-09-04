"""Unit tests for CloudFlareStorageService."""

from unittest.mock import MagicMock, patch
import pytest
import io

from app.common.config import Settings
from app.services.storage_service import (
    CloudFlareStorageService,
    GoogleDriveStorageService,
)


@patch("boto3.client")
def test_cloudflare_storage_upload_bytes(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    settings = Settings(
        ENVIRONMENT="staging",
        R2_ACCOUNT_ID="test_account",
        R2_ACCESS_KEY_ID="test_key",
        R2_SECRET_ACCESS_KEY="test_secret",
        R2_BUCKET_NAME="test_bucket",
        R2_PUBLIC_DOMAIN="https://cdn.example.com",
    )

    storage = CloudFlareStorageService(settings)
    url = storage.upload_bytes(b"hello world", "test/file.txt", "text/plain")

    assert url == "https://cdn.example.com/staging/test/file.txt"
    mock_s3.put_object.assert_called_once_with(
        Bucket="test_bucket",
        Key="staging/test/file.txt",
        Body=b"hello world",
        ContentType="text/plain",
    )


@patch("boto3.client")
def test_cloudflare_storage_upload_file_object(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    settings = Settings(
        ENVIRONMENT="production",
        R2_ACCOUNT_ID="test_account",
        R2_ACCESS_KEY_ID="test_key",
        R2_SECRET_ACCESS_KEY="test_secret",
        R2_BUCKET_NAME="test_bucket",
        R2_PUBLIC_DOMAIN="https://cdn.example.com",
    )

    storage = CloudFlareStorageService(settings)
    file_obj = io.BytesIO(b"file content")
    url = storage.upload(file_obj, "test/doc.pdf", "application/pdf")

    assert url == "https://cdn.example.com/production/test/doc.pdf"
    mock_s3.upload_fileobj.assert_called_once_with(
        file_obj,
        "test_bucket",
        "production/test/doc.pdf",
        ExtraArgs={"ContentType": "application/pdf"},
    )


@patch("boto3.client")
def test_cloudflare_storage_delete_file(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    settings = Settings(
        R2_ACCOUNT_ID="test_account",
        R2_ACCESS_KEY_ID="test_key",
        R2_SECRET_ACCESS_KEY="test_secret",
        R2_BUCKET_NAME="test_bucket",
        R2_PUBLIC_DOMAIN="https://cdn.example.com",
    )

    storage = CloudFlareStorageService(settings)
    res = storage.delete_file("https://cdn.example.com/test/file.txt")

    assert res is True
    mock_s3.delete_object.assert_called_once_with(
        Bucket="test_bucket", Key="test/file.txt"
    )


@patch("boto3.client")
def test_cloudflare_generate_presigned_url(mock_boto_client):
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://presigned.url/put"
    mock_boto_client.return_value = mock_s3

    settings = Settings(
        ENVIRONMENT="staging",
        R2_ACCOUNT_ID="test_account",
        R2_ACCESS_KEY_ID="test_key",
        R2_SECRET_ACCESS_KEY="test_secret",
        R2_BUCKET_NAME="test_bucket",
        R2_PUBLIC_DOMAIN="https://cdn.example.com",
    )

    storage = CloudFlareStorageService(settings)
    url = storage.generate_presigned_url("put_object", "users/123/profile.jpg", "image/jpeg", 3600)

    assert url == "https://presigned.url/put"
    mock_s3.generate_presigned_url.assert_called_once_with(
        ClientMethod="put_object",
        Params={"Bucket": "test_bucket", "Key": "staging/users/123/profile.jpg", "ContentType": "image/jpeg"},
        ExpiresIn=3600,
    )


@patch("googleapiclient.discovery.build")
@patch("google.oauth2.service_account.Credentials.from_service_account_info")
def test_google_drive_storage_upload_bytes(mock_creds, mock_build):
    mock_drive = MagicMock()
    mock_build.return_value = mock_drive
    mock_create = MagicMock()
    mock_drive.files.return_value.create.return_value = mock_create
    mock_create.execute.return_value = {
        "id": "1AbCdEfGh12345",
        "name": "file.txt",
        "webViewLink": "https://drive.google.com/file/d/1AbCdEfGh12345/view",
    }

    settings = Settings(
        GOOGLE_DRIVE_CREDENTIALS_JSON='{"type": "service_account"}',
        GOOGLE_DRIVE_FOLDER_ID="test_folder_123",
    )

    storage = GoogleDriveStorageService(settings)
    url = storage.upload_bytes(b"gdrive test data", "folder/file.txt", "text/plain")

    assert url == "https://drive.google.com/file/d/1AbCdEfGh12345/view"
    mock_drive.files().create.assert_called_once()


@patch("googleapiclient.discovery.build")
@patch("google.oauth2.service_account.Credentials.from_service_account_info")
def test_google_drive_storage_delete_file(mock_creds, mock_build):
    mock_drive = MagicMock()
    mock_build.return_value = mock_drive
    mock_delete = MagicMock()
    mock_drive.files.return_value.delete.return_value = mock_delete
    mock_delete.execute.return_value = {}

    settings = Settings(
        GOOGLE_DRIVE_CREDENTIALS_JSON='{"type": "service_account"}',
        GOOGLE_DRIVE_FOLDER_ID="test_folder_123",
    )

    storage = GoogleDriveStorageService(settings)
    res = storage.delete_file("1AbCdEfGh12345")

    mock_drive.files().delete.assert_called_once_with(
        fileId="1AbCdEfGh12345", supportsAllDrives=True
    )
