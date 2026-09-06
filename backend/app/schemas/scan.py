from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class ScanCreateResponse(BaseModel):
    scanId: UUID


class ImageUploadResponse(BaseModel):
    imageId: UUID


class SubmitResponse(BaseModel):
    ok: bool
    status: str


class PairTokenResponse(BaseModel):
    token: str
    joinUrl: str
    expiresAt: str


class PairSubmitResponse(BaseModel):
    ok: bool
    scanId: str
    status: str


class ScanImageOut(BaseModel):
    imageId: UUID
    panelType: str
    width: Optional[int] = None
    height: Optional[int] = None
    viewUrl: str


class FieldOut(BaseModel):
    fieldName: str
    fieldValue: Optional[str] = None
    confidence: Optional[float] = None
    panelType: Optional[str] = None
    imageId: Optional[UUID] = None
    bbox: Optional[dict[str, Any]] = None


class ViolationOut(BaseModel):
    ruleCode: str
    severity: str
    field: Optional[str] = None
    message: str
    panelType: Optional[str] = None
    imageId: Optional[UUID] = None
    bbox: Optional[dict[str, Any]] = None


class ReportOut(BaseModel):
    pdfUrl: Optional[str] = None
    jsonUrl: Optional[str] = None


class ScanListItem(BaseModel):
    scanId: UUID
    status: str
    score: Optional[float] = None
    createdAt: str


class ScanOut(BaseModel):
    scanId: UUID
    status: str
    score: Optional[float] = None
    images: list[ScanImageOut] = []
    fields: list[FieldOut] = []
    violations: list[ViolationOut] = []
    report: ReportOut = ReportOut()
    error: Optional[str] = None