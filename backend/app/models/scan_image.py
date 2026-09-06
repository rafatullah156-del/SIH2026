import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.scan import Base


class PanelType(str, enum.Enum):
    front = "front"
    back = "back"
    side = "side"
    calibration = "calibration"


class ScanImage(Base):
    __tablename__ = "scan_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        index=True,
    )
    panel_type: Mapped[PanelType] = mapped_column(
        Enum(PanelType, name="paneltype"), index=True
    )
    object_key: Mapped[str] = mapped_column(String, index=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )