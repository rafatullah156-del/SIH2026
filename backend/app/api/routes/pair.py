import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_token
from app.models.pair_token import PairToken
from app.models.scan import Scan, ScanStatus
from app.models.scan_image import PanelType, ScanImage
from app.schemas.scan import PairTokenResponse, PairSubmitResponse
from app.services.storage import upload_fileobj
from app.workers.tasks import process_scan

router = APIRouter(tags=["pairing"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/scans/{scan_id}/pair-token", response_model=PairTokenResponse)
def create_pair_token(scan_id: UUID, request: Request, db: Session = Depends(get_db)):
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    plain = secrets.token_urlsafe(32)
    th = hash_token(plain)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.PAIR_TOKEN_TTL_SECONDS)

    pt = PairToken(scan_id=scan_id, token_hash=th, expires_at=expires_at)
    db.add(pt)
    db.commit()

    origin = request.headers.get("origin")  # Cloudflare Pages domain will be here
    if origin and origin.startswith("http"):
        join_url = f"{origin.rstrip('/')}/quick-upload?t={plain}"
    elif settings.FRONTEND_QUICK_UPLOAD_BASE_URL:
        join_url = f"{settings.FRONTEND_QUICK_UPLOAD_BASE_URL}?t={plain}"
    else:
        join_url = f"{str(request.base_url).rstrip('/')}/quick-upload?t={plain}"

    return PairTokenResponse(token=plain, joinUrl=join_url, expiresAt=expires_at.isoformat())


@router.post("/pair/{token}/submit", response_model=PairSubmitResponse)
def pair_submit(
    token: str,
    front: UploadFile = File(...),
    back: UploadFile = File(...),
    calibration: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    th = hash_token(token)
    pt = db.query(PairToken).filter(PairToken.token_hash == th).first()

    if not pt:
        raise HTTPException(status_code=404, detail="Invalid token")

    now = datetime.now(timezone.utc)

    if pt.used_at is not None:
        raise HTTPException(status_code=409, detail="Token already used")

    if pt.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=410, detail="Token expired")

    if settings.FONT_CHECK_ENABLED and calibration is None:
        raise HTTPException(status_code=400, detail="Calibration image required")

    scan = db.get(Scan, pt.scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # mark token used immediately (one-time use)
    pt.used_at = now
    db.commit()

    def _put(panel: PanelType, uf: UploadFile):
        key = f"scans/{scan.id}/{panel.value}.jpg"
        upload_fileobj(uf.file, key, content_type=uf.content_type or "image/jpeg")
        existing = (
            db.query(ScanImage)
            .filter(ScanImage.scan_id == scan.id, ScanImage.panel_type == panel)
            .first()
        )
        if existing:
            existing.object_key = key
        else:
            db.add(ScanImage(scan_id=scan.id, panel_type=panel, object_key=key))

    _put(PanelType.front, front)
    _put(PanelType.back, back)
    if calibration is not None:
        _put(PanelType.calibration, calibration)

    scan.status = ScanStatus.queued
    scan.error = None
    db.commit()

    process_scan.delay(str(scan.id))
    return PairSubmitResponse(ok=True, scanId=str(scan.id), status="queued")
