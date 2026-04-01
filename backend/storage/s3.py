import logging
from functools import lru_cache
from io import BufferedIOBase
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.s3_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def upload_file(
    local_path: str | Path,
    s3_key: str,
    bucket: str | None = None,
) -> str:
    """Upload a local file to S3 and return the S3 key."""
    bucket = bucket or settings.s3_bucket_name
    client = _get_s3_client()
    client.upload_file(str(local_path), bucket, s3_key)
    logger.info("Uploaded '%s' → s3://%s/%s", local_path, bucket, s3_key)
    return s3_key


def upload_fileobj(
    file_obj: BufferedIOBase,
    s3_key: str,
    bucket: str | None = None,
) -> str:
    """Upload a file-like object to S3 and return the S3 key."""
    bucket = bucket or settings.s3_bucket_name
    client = _get_s3_client()
    client.upload_fileobj(file_obj, bucket, s3_key)
    logger.info("Uploaded stream → s3://%s/%s", bucket, s3_key)
    return s3_key


def download_file(
    s3_key: str,
    local_path: str | Path,
    bucket: str | None = None,
) -> Path:
    """Download an S3 object to a local path."""
    bucket = bucket or settings.s3_bucket_name
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    client = _get_s3_client()
    client.download_file(bucket, s3_key, str(local_path))
    logger.info("Downloaded s3://%s/%s → '%s'", bucket, s3_key, local_path)
    return local_path


def delete_object(
    s3_key: str,
    bucket: str | None = None,
) -> None:
    """Delete a single object from S3."""
    bucket = bucket or settings.s3_bucket_name
    client = _get_s3_client()
    client.delete_object(Bucket=bucket, Key=s3_key)
    logger.info("Deleted s3://%s/%s", bucket, s3_key)


def generate_presigned_url(
    s3_key: str,
    bucket: str | None = None,
    expiration: int = 3600,
) -> str:
    """Generate a presigned URL for temporary access to a private object."""
    bucket = bucket or settings.s3_bucket_name
    client = _get_s3_client()
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=expiration,
        )
    except ClientError:
        logger.exception("Failed to generate presigned URL for '%s'", s3_key)
        raise
    return url
