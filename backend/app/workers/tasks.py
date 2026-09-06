import uuid

from app.workers.celery_app import celery_app
from app.core.db import SessionLocal
from app.core.logging import logger
from app.models.scan import Scan, ScanStatus
from app.models.scan_image import ScanImage, PanelType
from app.models.field import ExtractedField
from app.models.violation import Violation, Severity
from app.models.report import Report
from app.services.storage import download_bytes, upload_bytes
from app.services.preprocessing import prepare_image, map_bbox_to_display
from app.services.ocr import run_ocr, ocr_stats
from app.services.extraction import extract_fields, MANDATORY_FIELDS
from app.services.calibration import estimate_mm_per_px
from app.services.rules import run_rules
from app.services.report_gen import generate_pdf, generate_json_report

PUBLIC_FIELD_KEYS = ("field_name", "field_value", "confidence", "panel_type", "scan_image_id", "bbox")
PUBLIC_VIOLATION_KEYS = ("rule_code", "severity", "field", "message", "panel_type", "scan_image_id", "bbox")
PRESENCE_CONF = 0.5


def _public(d: dict, keys) -> dict:
    return {k: d.get(k) for k in keys}


def _merge_fields(per_image: list[list[dict]], fallback_where: dict) -> tuple[dict, dict]:
    """Best candidate per field across all panels + presence map."""
    best: dict[str, dict] = {}
    presence: dict[str, set[str]] = {}
    for fields in per_image:
        for f in fields:
            name = f["field_name"]
            has_value = bool(f.get("field_value"))
            if has_value and f.get("confidence", 0) >= PRESENCE_CONF:
                presence.setdefault(name, set()).add(f.get("panel_type"))
            cur = best.get(name)
            if cur is None:
                best[name] = f
                continue
            cur_has = bool(cur.get("field_value"))
            if (has_value and not cur_has) or (has_value == cur_has and f.get("confidence", 0) > cur.get("confidence", 0)):
                best[name] = f
            elif not has_value and not cur_has:
                # prefer the one where at least the label was found
                if (f.get("meta") or {}).get("label_found") and not (cur.get("meta") or {}).get("label_found"):
                    best[name] = f
    for name in MANDATORY_FIELDS:
        if name not in best:
            best[name] = {
                "field_name": name, "field_value": None, "confidence": 0.0,
                "panel_type": fallback_where["panel_type"], "scan_image_id": fallback_where["scan_image_id"],
                "bbox": None, "meta": {"label_found": False},
            }
    return best, presence


@celery_app.task(name="app.workers.tasks.process_scan", bind=True, max_retries=2)
def process_scan(self, scan_id: str):
    sid = uuid.UUID(scan_id)
    db = SessionLocal()
    try:
        scan = db.get(Scan, sid)
        if not scan:
            logger.error(f"Scan {scan_id} not found")
            return

        scan.status = ScanStatus.processing
        db.commit()
        logger.info(f"Processing scan {scan_id}")

        # clean old results (for re-runs)
        db.query(ExtractedField).filter(ExtractedField.scan_id == sid).delete()
        db.query(Violation).filter(Violation.scan_id == sid).delete()
        db.commit()

        images = db.query(ScanImage).filter(ScanImage.scan_id == sid).all()
        if not images:
            raise RuntimeError("No images attached to scan")

        images_by_id = {str(im.id): im for im in images}
        front = next((im for im in images if im.panel_type == PanelType.front), images[0])
        default_where = {"panel_type": front.panel_type.value, "scan_image_id": str(front.id)}

        per_image_fields: list[list[dict]] = []
        image_quality: list[dict] = []
        mm_per_px = None
        calibration_note = "no calibration image provided"

        for image in images:
            panel = image.panel_type.value
            logger.info(f"Processing image {image.id} panel={panel}")
            raw_bytes = download_bytes(image.object_key)

            if image.panel_type == PanelType.calibration:
                cal = estimate_mm_per_px(raw_bytes)
                if cal:
                    mm_per_px = cal["mm_per_px"]
                    calibration_note = None
                    logger.info(f"Calibration OK: {mm_per_px:.5f} mm/px (conf {cal['confidence']})")
                else:
                    calibration_note = "reference card not detected in calibration image"
                    logger.warning("Calibration image present but reference card not detected")
                continue

            prep = prepare_image(raw_bytes)
            image.width = prep.display_width
            image.height = prep.display_height

            blocks = run_ocr(prep.working_bytes)
            for b in blocks:
                b["bbox"] = map_bbox_to_display(b["bbox"], prep.scale)
            stats = ocr_stats(blocks)
            logger.info(f"  blur={prep.blur} blocks={stats['n_blocks']} mean_conf={stats['mean_conf']}")
            if blocks:
                logger.debug("  OCR text: " + " | ".join(b["text"] for b in blocks[:60]))

            image_quality.append({
                "scan_image_id": str(image.id), "panel_type": panel,
                "blur": prep.blur, "mean_conf": stats["mean_conf"], "n_blocks": stats["n_blocks"],
            })
            per_image_fields.append(extract_fields(blocks, panel, image.id))

        db.commit()

        merged, presence = _merge_fields(per_image_fields, default_where)
        violations, final_score = run_rules(
            merged,
            panel_presence=presence,
            image_quality=image_quality,
            mm_per_px=mm_per_px,
            calibration_note=calibration_note,
            default_where=default_where,
        )

        # persist fields (one row per field name; mandatory first, then optional extras found)
        ordered = [merged[n] for n in MANDATORY_FIELDS] + [f for n, f in merged.items() if n not in MANDATORY_FIELDS]
        for f in ordered:
            img = images_by_id.get(str(f.get("scan_image_id")))
            db.add(ExtractedField(
                scan_id=sid,
                field_name=f["field_name"],
                field_value=f.get("field_value"),
                confidence=f.get("confidence"),
                panel_type=img.panel_type if img else None,
                scan_image_id=img.id if img else None,
                bbox=f.get("bbox"),
            ))

        for v in violations:
            img = images_by_id.get(str(v.get("scan_image_id")))
            db.add(Violation(
                scan_id=sid,
                rule_code=v["rule_code"],
                severity=Severity(v["severity"]),
                field=v.get("field"),
                message=v["message"],
                panel_type=img.panel_type if img else None,
                scan_image_id=img.id if img else None,
                bbox=v.get("bbox"),
            ))
        db.commit()

        # reports
        pub_fields = [_public(f, PUBLIC_FIELD_KEYS) for f in ordered]
        pub_viol = [_public(v, PUBLIC_VIOLATION_KEYS) for v in violations]
        pdf_bytes = generate_pdf(scan_id, pub_fields, pub_viol)
        json_bytes = generate_json_report(scan_id, pub_fields, pub_viol, final_score)

        pdf_key = f"reports/{scan_id}.pdf"
        json_key = f"reports/{scan_id}.json"
        upload_bytes(pdf_bytes, pdf_key, content_type="application/pdf")
        upload_bytes(json_bytes, json_key, content_type="application/json")

        rep = db.query(Report).filter(Report.scan_id == sid).first()
        if not rep:
            rep = Report(scan_id=sid)
            db.add(rep)
        rep.pdf_key = pdf_key
        rep.json_key = json_key

        scan.score = final_score
        scan.status = ScanStatus.done
        scan.error = None
        db.commit()
        logger.info(f"Scan {scan_id} done. Score={final_score} violations={len(violations)}")

    except Exception as exc:
        logger.exception(f"Scan {scan_id} failed: {exc}")
        try:
            db.rollback()
            scan = db.get(Scan, sid)
            if scan:
                scan.status = ScanStatus.failed
                scan.error = str(exc)[:1000]
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=5)
    finally:
        db.close()