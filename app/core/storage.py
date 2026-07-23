import logging
from typing import Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageClient:
    """
    AWS S3 / MinIO client wrapper responsible for generating secure pre-signed URLs
    for binary object upload and retrieval (problem PDFs, visual assets, testcases).
    Ensure no raw data binaries are saved directly inside PostgreSQL.
    """

    def __init__(self) -> None:
        client_config = Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        )
        boto_kwargs = {
            "service_name": "s3",
            "region_name": settings.STORAGE_REGION,
            "aws_access_key_id": settings.STORAGE_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.STORAGE_SECRET_ACCESS_KEY,
            "config": client_config,
        }
        if settings.STORAGE_ENDPOINT_URL:
            boto_kwargs["endpoint_url"] = settings.STORAGE_ENDPOINT_URL

        self.client = boto3.client(**boto_kwargs)
        self.bucket = settings.STORAGE_BUCKET_NAME

    def generate_presigned_get_url(
        self,
        object_key: str,
        expires_in: Optional[int] = None,
    ) -> str:
        """
        Generate a pre-signed URL for downloading a binary object (e.g. problem statement PDF).
        """
        if expires_in is None:
            expires_in = settings.PRESIGNED_URL_EXPIRE_SECONDS
        try:
            url = self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": object_key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating GET pre-signed URL for {object_key}: {e}")
            raise RuntimeError(f"Failed to generate download URL for object: {object_key}") from e

    def generate_presigned_put_url(
        self,
        object_key: str,
        content_type: str = "application/pdf",
        expires_in: Optional[int] = None,
    ) -> str:
        """
        Generate a pre-signed URL for uploading a binary object directly to S3/MinIO.
        """
        if expires_in is None:
            expires_in = settings.PRESIGNED_URL_EXPIRE_SECONDS
        try:
            url = self.client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": object_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating PUT pre-signed URL for {object_key}: {e}")
            raise RuntimeError(f"Failed to generate upload URL for object: {object_key}") from e


# Global singleton client instance
storage_client = StorageClient()
