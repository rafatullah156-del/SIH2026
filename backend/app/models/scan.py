import enum
import uuid

from sqlalchemy import DateTime, Enum, Float, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ScanStatus(str, enum.Enum):
    created = "created"
    uploading = "uploading"
    queued = "queued"
    processing = "processing"
    done = "done"
    failed = "failed"


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, name="scanstatus"),
        default=ScanStatus.created,
        index=True,
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )