from sqlalchemy import Column, String, LargeBinary, DateTime, func
from app.models.scan import Base

class StoredObject(Base):
    __tablename__ = "stored_objects"

    object_key = Column(String, primary_key=True, index=True)
    content_type = Column(String, nullable=False, default="application/octet-stream")
    data = Column(LargeBinary, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)