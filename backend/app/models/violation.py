import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.scan import Base
from app.models.scan_image import PanelType


class Severity(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Violation(Base):
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        index=True,
    )
    rule_code: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity"), index=True
    )
    field: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str] = mapped_column(String)

    panel_type: Mapped[PanelType | None] = mapped_column(nullable=True)
    scan_image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scan_images.id"),
        nullable=True,
    )
    bbox: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )