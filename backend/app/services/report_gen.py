"""
Phase A: stub — returns empty bytes.
Phase C: implement ReportLab PDF generation.
"""
from typing import Any


def generate_pdf(scan_id: str, fields: list[dict], violations: list[dict]) -> bytes:
    """
    Returns PDF bytes.
    Phase A: returns a minimal placeholder PDF so the endpoint doesn't crash.
    """
    # minimal valid PDF so boto3 upload doesn't fail
    placeholder = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f\n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )
    return placeholder


def generate_json_report(
    scan_id: str,
    fields: list[dict[str, Any]],
    violations: list[dict[str, Any]],
    score: float,
) -> bytes:
    import json
    report = {
        "scanId": scan_id,
        "score": score,
        "fields": fields,
        "violations": violations,
    }
    return json.dumps(report, indent=2, default=str).encode("utf-8")