import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import logger


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
    )


def upload_fileobj(fileobj, object_key: str, content_type: str = "application/octet-stream") -> None:
    try:
        _s3().upload_fileobj(
            fileobj,
            settings.S3_BUCKET,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )
        logger.info(f"Uploaded {object_key}")
    except ClientError as e:
        logger.error(f"Upload failed for {object_key}: {e}")
        raise


def upload_bytes(data: bytes, object_key: str, content_type: str = "application/octet-stream") -> None:
    import io
    upload_fileobj(io.BytesIO(data), object_key, content_type)


def get_object_stream(object_key: str):
    try:
        obj = _s3().get_object(Bucket=settings.S3_BUCKET, Key=object_key)
        return obj["Body"], obj.get("ContentType", "application/octet-stream")
    except ClientError as e:
        logger.error(f"Download failed for {object_key}: {e}")
        raise


def download_bytes(object_key: str) -> bytes:
    body, _ = get_object_stream(object_key)
    return body.read()