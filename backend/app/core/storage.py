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
