import io
import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.core.logging import logger
from app.models.scan import Base
from app.models.object_store import StoredObject

_initialized = False


def _ensure_tables():
    global _initialized
    if not _initialized:
        Base.metadata.create_all(bind=engine)
        _initialized = True


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
    )


def _db() -> Session:
    return SessionLocal()


def upload_fileobj(fileobj, object_key: str, content_type: str = "application/octet-stream") -> None:
    # Postgres storage (default)
    if settings.STORAGE_BACKEND.lower() == "postgres":
        _ensure_tables()
        data = fileobj.read()
        db = _db()
        try:
            obj = db.get(StoredObject, object_key)
            if obj:
                obj.data = data
                obj.content_type = content_type
            else:
                db.add(StoredObject(object_key=object_key, data=data, content_type=content_type))
            db.commit()
            logger.info(f"[pg-storage] saved {object_key} ({len(data)} bytes)")
            return
        finally:
            db.close()

    # S3 fallback
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
    upload_fileobj(io.BytesIO(data), object_key, content_type)


def get_object_stream(object_key: str):
    if settings.STORAGE_BACKEND.lower() == "postgres":
        _ensure_tables()
        db = _db()
        try:
            obj = db.get(StoredObject, object_key)
            if not obj:
                raise FileNotFoundError(object_key)
            return io.BytesIO(obj.data), (obj.content_type or "application/octet-stream")
        finally:
            db.close()

    try:
        obj = _s3().get_object(Bucket=settings.S3_BUCKET, Key=object_key)
        return obj["Body"], obj.get("ContentType", "application/octet-stream")
    except ClientError as e:
        logger.error(f"Download failed for {object_key}: {e}")
        raise


def download_bytes(object_key: str) -> bytes:
    body, _ = get_object_stream(object_key)
    return body.read()
