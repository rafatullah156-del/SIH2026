from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.db import SessionLocal
from app.models.scan import Scan, ScanStatus
from app.models.violation import Violation, Severity

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/summary")
def dashboard_summary(
    from_date: str | None = None,
    to_date: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Scan)

    if from_date:
        query = query.filter(Scan.created_at >= from_date)
    if to_date:
        query = query.filter(Scan.created_at <= to_date)

    total = query.count()
    done = query.filter(Scan.status == ScanStatus.done).count()
    failed = query.filter(Scan.status == ScanStatus.failed).count()

    avg_score = (
        db.query(func.avg(Scan.score))
        .filter(Scan.status == ScanStatus.done)
        .scalar()
    )

    high_viol = db.query(Violation).filter(Violation.severity == Severity.high).count()
    med_viol = db.query(Violation).filter(Violation.severity == Severity.medium).count()
    low_viol = db.query(Violation).filter(Violation.severity == Severity.low).count()

    return {
        "totalScans": total,
        "doneScans": done,
        "failedScans": failed,
        "avgScore": round(float(avg_score), 2) if avg_score else 0.0,
        "violations": {
            "high": high_viol,
            "medium": med_viol,
            "low": low_viol,
        },
    }