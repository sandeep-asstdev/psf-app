"""
================================================================================
FILE PURPOSE: MinIO / S3 Object Storage File Management.
This file handles uploading, downloading, and managing physical files (DMS import files,
error Excel reports, audio recordings, customer survey attachments) in MinIO S3 object storage.

KEY RESPONSIBILITIES:
- Initializes default S3 buckets (`psf-documents`, `psf-exports`) during app startup (`init_storage_buckets`).
- Uploads file byte streams to S3 with content-type detection (`upload_file`).
- Downloads file bytes from S3 (`download_file`).
- Generates secure presigned download URLs.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: botocore.exceptions.EndpointConnectionError: Could not connect to the endpoint URL http://minio:9000
  -> Cause: The MinIO storage container (psf_minio) is stopped or not reachable.
  -> What should you do: Run `docker ps` to verify psf_minio is running. Run `docker compose up -d minio` to restart it.
- Error: botocore.exceptions.ClientError: NoSuchBucket
  -> Cause: The target S3 bucket does not exist.
  -> What should you do: Restart psf_api (`docker restart psf_api`) to trigger `init_storage_buckets()` which auto-creates required buckets.
================================================================================
"""
import logging
from typing import Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger("psf.storage")


def get_s3_client():
    """Return a configured boto3 S3 client for MinIO or AWS S3."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL if settings.STORAGE_BACKEND == "minio" else None,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4"),
    )


async def init_storage_buckets() -> None:
    """Ensure required buckets exist upon service startup."""
    try:
        s3 = get_s3_client()
        required_buckets = [settings.S3_BUCKET_DOCUMENTS, settings.S3_BUCKET_EXPORTS]

        existing = []
        try:
            response = s3.list_buckets()
            existing = [b["Name"] for b in response.get("Buckets", [])]
        except Exception as e:
            logger.warning(f"Could not list S3 buckets (MinIO may still be starting): {e}")
            return

        for bucket in required_buckets:
            if bucket not in existing:
                try:
                    s3.create_bucket(Bucket=bucket)
                    logger.info(f"Created S3 bucket: {bucket}")
                except ClientError as ce:
                    logger.warning(f"Bucket creation error for {bucket}: {ce}")
    except Exception as e:
        logger.warning(f"Storage bucket init warning: {e}")

