import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.scan import Scan, ScanStatus
from app.models.scan_image import ScanImage, PanelType
from app.models.field import ExtractedField
from app.models.violation import Violation
from app.models.report import Report
from app.schemas.scan import (
    ScanCreateResponse,
    ImageUploadResponse,
    SubmitResponse,
    ScanOut,
    ScanListItem,
)
from app.services.storage import upload_fileobj, get_object_stream
from app.workers.tasks import process_scan

router = APIRouter(prefix="/scans", tags=["scans"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _required_panels() -> set:
    base = {PanelType.front, PanelType.back}
    if settings.FONT_CHECK_ENABLED:
        base.add(PanelType.calibration)
    return base


@router.post("", response_model=ScanCreateResponse)
def create_scan(db: Session = Depends(get_db)):
    scan = Scan(status=ScanStatus.created)
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return ScanCreateResponse(scanId=scan.id)


@router.post("/{scan_id}/images", response_model=ImageUploadResponse)
def upload_image(
    scan_id: uuid.UUID,
    panelType: PanelType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    object_key = f"scans/{scan_id}/{panelType.value}.jpg"
    upload_fileobj(file.file, object_key, content_type=file.content_type or "image/jpeg")

    existing = (
        db.query(ScanImage)
        .filter(ScanImage.scan_id == scan_id, ScanImage.panel_type == panelType)
        .first()
    )
    if existing:
        existing.object_key = object_key
        image = existing
    else:
        image = ScanImage(
            scan_id=scan_id,
            panel_type=panelType,
            object_key=object_key,
        )
        db.add(image)

    if scan.status == ScanStatus.created:
        scan.status = ScanStatus.uploading

    db.commit()
    db.refresh(image)
    return ImageUploadResponse(imageId=image.id)


@router.post("/{scan_id}/submit", response_model=SubmitResponse)
def submit_scan(scan_id: uuid.UUID, db: Session = Depends(get_db)):
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    imgs = db.query(ScanImage).filter(ScanImage.scan_id == scan_id).all()
    have = {i.panel_type for i in imgs}
    missing = [p.value for p in _required_panels() if p not in have]

    if missing:
        raise HTTPException(
            status_code=400,
            detail={"detail": "Missing required images", "missing": missing},
        )

    scan.status = ScanStatus.queued
    scan.error = None
    db.commit()

    process_scan.delay(str(scan_id))
    return SubmitResponse(ok=True, status="queued")


@router.get("", response_model=list[ScanListItem])
def list_scans(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    scans = (
        db.query(Scan)
        .order_by(Scan.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        ScanListItem(
            scanId=s.id,
            status=s.status.value,
            score=s.score,
            createdAt=s.created_at.isoformat(),
        )
        for s in scans
    ]


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: uuid.UUID, db: Session = Depends(get_db)):
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    imgs = db.query(ScanImage).filter(ScanImage.scan_id == scan_id).all()
    fields = db.query(ExtractedField).filter(ExtractedField.scan_id == scan_id).all()
    viols = db.query(Violation).filter(Violation.scan_id == scan_id).all()
    report = db.query(Report).filter(Report.scan_id == scan_id).first()

    images_out = [
        {
            "imageId": im.id,
            "panelType": im.panel_type.value,
            "width": im.width,
            "height": im.height,
            "viewUrl": f"/scans/{scan_id}/images/{im.id}",
        }
        for im in imgs
    ]

    fields_out = [
        {
            "fieldName": f.field_name,
            "fieldValue": f.field_value,
            "confidence": f.confidence,
            "panelType": f.panel_type.value if f.panel_type else None,
            "imageId": f.scan_image_id,
            "bbox": f.bbox,
        }
        for f in fields
    ]

    viols_out = [
        {
            "ruleCode": v.rule_code,
            "severity": v.severity.value,
            "field": v.field,
            "message": v.message,
            "panelType": v.panel_type.value if v.panel_type else None,
            "imageId": v.scan_image_id,
            "bbox": v.bbox,
        }
        for v in viols
    ]

    report_out = {
        "pdfUrl": f"/scans/{scan_id}/report.pdf" if (report and report.pdf_key) else None,
        "jsonUrl": f"/scans/{scan_id}/report.json" if (report and report.json_key) else None,
    }

    return ScanOut(
        scanId=scan.id,
        status=scan.status.value,
        score=scan.score,
        images=images_out,
        fields=fields_out,
        violations=viols_out,
        report=report_out,
        error=scan.error,
    )


@router.get("/{scan_id}/images/{image_id}")
def view_image(scan_id: uuid.UUID, image_id: uuid.UUID, db: Session = Depends(get_db)):
    image = db.get(ScanImage, image_id)
    if not image or image.scan_id != scan_id:
        raise HTTPException(status_code=404, detail="Image not found")
    body, content_type = get_object_stream(image.object_key)
    return StreamingResponse(body, media_type=content_type)


@router.get("/{scan_id}/report.pdf")
def download_pdf(scan_id: uuid.UUID, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.scan_id == scan_id).first()
    if not report or not report.pdf_key:
        raise HTTPException(status_code=404, detail="PDF report not ready")
    body, _ = get_object_stream(report.pdf_key)
    return StreamingResponse(body, media_type="application/pdf")


@router.get("/{scan_id}/report.json")
def download_json(scan_id: uuid.UUID, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.scan_id == scan_id).first()
    if not report or not report.json_key:
        raise HTTPException(status_code=404, detail="JSON report not ready")
    body, _ = get_object_stream(report.json_key)
    return StreamingResponse(body, media_type="application/json")