"""S3-compatible storage abstraction (MinIO / AWS S3).

Uses asyncio.to_thread to avoid blocking the event loop with boto3's sync calls.
"""

import asyncio
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings


class StorageService:
    """Handles file uploads and downloads to S3/MinIO."""

    def __init__(self):
        self._client = None
        self.bucket = settings.s3_bucket_name

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
                config=Config(signature_version="s3v4"),
            )
        return self._client

    async def ensure_bucket(self) -> None:
        def _ensure():
            try:
                self.client.head_bucket(Bucket=self.bucket)
            except ClientError:
                self.client.create_bucket(Bucket=self.bucket)
        await asyncio.to_thread(_ensure)

    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: str = "uploads",
    ) -> str:
        """Upload file and return the storage key."""
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        key = f"{folder}/{uuid.uuid4().hex}.{ext}" if ext else f"{folder}/{uuid.uuid4().hex}"

        def _upload():
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_data,
                ContentType=content_type,
            )

        await asyncio.to_thread(_upload)
        return key

    async def download_file(self, key: str) -> bytes:
        """Download a file by key."""
        def _download():
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        return await asyncio.to_thread(_download)

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for temporary access."""
        def _presign():
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        return await asyncio.to_thread(_presign)

    async def delete_file(self, key: str) -> None:
        """Delete a file by key."""
        await asyncio.to_thread(
            self.client.delete_object, Bucket=self.bucket, Key=key
        )

    def get_public_url(self, key: str) -> str:
        """Get URL accessible from the browser."""
        base = settings.s3_public_url or settings.s3_endpoint_url
        return f"{base}/{self.bucket}/{key}"


storage_service = StorageService()
