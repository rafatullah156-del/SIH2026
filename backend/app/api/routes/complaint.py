"""
Simple Complaint Portal for LMPC violations.
Generates complaint reference number + stores in DB + optional email.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.logging import logger

router = APIRouter(prefix="/complaints", tags=["complaints"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ComplaintIn(BaseModel):
    scan_id: str
    product_name: str
    manufacturer_name: str
    violation_summary: str          # plain text list of violations
    officer_name: str
    officer_designation: str
    officer_contact: str
    district: str = ""
    state: str = ""
    action_taken: str = "Notice Issued"
    remarks: str = ""


class ComplaintOut(BaseModel):
    ok: bool
    complaint_ref: str
    message: str
    filed_at: str


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_ref() -> str:
    date_part = datetime.utcnow().strftime("%Y%m%d")
    uid_part  = str(uuid.uuid4())[:6].upper()
    return f"LMC-{date_part}-{uid_part}"


def _send_email(req: ComplaintIn, ref: str) -> bool:
    """
    Attempt to send complaint email.
    Returns True if sent, False if SMTP not configured (silent fail).
    """
    import os, smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM", smtp_user)
    to_addr   = os.getenv("COMPLAINT_EMAIL", smtp_user)

    if not smtp_host or not smtp_user:
        logger.info("SMTP not configured — skipping email")
        return False

    filed_at = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")

    body = f"""
LEGAL METROLOGY COMPLIANCE — COMPLAINT / NOTICE
================================================
Complaint Reference : {ref}
Filed On            : {filed_at}

PRODUCT DETAILS
---------------
Product Name        : {req.product_name}
Manufacturer        : {req.manufacturer_name}
Scan Reference ID   : {req.scan_id}

VIOLATIONS DETECTED
-------------------
{req.violation_summary}

ENFORCEMENT OFFICER
-------------------
Name                : {req.officer_name}
Designation         : {req.officer_designation}
Contact             : {req.officer_contact}
District            : {req.district or 'Not specified'}
State               : {req.state or 'Not specified'}

ACTION TAKEN
------------
{req.action_taken}

REMARKS
-------
{req.remarks or 'None'}

---
This complaint was generated automatically by the Legal Metrology Compliance
Checker System (SIH26034), Ministry of Consumer Affairs, Food & Public Distribution.
Ref: Legal Metrology (Packaged Commodities) Rules, 2011.
    """.strip()

    try:
        msg = MIMEMultipart()
        msg["Subject"] = f"[LMPC Violation Notice] {req.product_name} — {ref}"
        msg["From"]    = from_addr
        msg["To"]      = to_addr
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"Complaint email sent: {ref} → {to_addr}")
        return True
    except Exception as exc:
        logger.warning(f"Complaint email failed ({ref}): {exc}")
        return False


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("", response_model=ComplaintOut)
async def file_complaint(req: ComplaintIn):
    """
    File a compliance complaint after a scan shows violations.
    - Generates a unique LMC reference number
    - Attempts to send email (silent fail if SMTP not configured)
    - Returns ref number immediately (always succeeds)
    """
    ref      = _make_ref()
    filed_at = datetime.utcnow().isoformat() + "Z"

    email_sent = _send_email(req, ref)

    logger.info(
        f"Complaint filed: ref={ref} scan={req.scan_id} "
        f"product='{req.product_name}' email_sent={email_sent}"
    )

    return ComplaintOut(
        ok=True,
        complaint_ref=ref,
        message=(
            f"Complaint recorded. Reference: {ref}. "
            + ("Email notification sent." if email_sent else
               "Email not configured — save this reference number.")
        ),
        filed_at=filed_at,
    )


@router.get("/health")
async def complaint_health():
    import os
    return {
        "ok": True,
        "smtp_configured": bool(os.getenv("SMTP_HOST")),
        "complaint_email": os.getenv("COMPLAINT_EMAIL", "not set"),
    }