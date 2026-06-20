"""ONOC-compatible e-Challan draft export."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from config import EVIDENCE_DIR
from services.challan.penalties import penalty_for_violation
from services.challan.receipt import VIOLATION_LABELS, render_receipt_html

VIOLATION_SECTION_MAP = {
    "helmet_non_compliance": "194D",
    "triple_riding": "194C",
    "wrong_side_driving": "184",
    "illegal_parking": "122",
    "seatbelt_non_compliance": "194B",
    "stop_line_violation": "177",
    "red_light_violation": "177",
}


def challan_number_for(evidence_id: str, generated_at: datetime | None = None) -> str:
    when = generated_at or datetime.now(timezone.utc)
    suffix = (evidence_id or "00000000").replace("-", "")[:8].upper()
    return f"ECH{when.year}{suffix}"


def build_challan_export(
    evidence_row: Any,
    officer_id: str = "OFFICER_DEMO",
) -> dict:
    """Build ONOC-shaped challan JSON for confirmed violations."""
    plate = evidence_row.plate_normalized or "UNKNOWN"
    raw_type = evidence_row.violation_type or ""
    types = [t.strip() for t in raw_type.split(",") if t.strip() and t.strip() != "none"]
    violation_type = types[0] if len(types) == 1 else raw_type
    now = datetime.now(timezone.utc)
    due = now + timedelta(days=60)
    fine = sum(penalty_for_violation(t) for t in types) if types else penalty_for_violation(raw_type)
    labels = [VIOLATION_LABELS.get(t, t.replace("_", " ").title()) for t in types]
    violation_label = " + ".join(labels) if labels else VIOLATION_LABELS.get(raw_type, raw_type.replace("_", " ").title())
    section = VIOLATION_SECTION_MAP.get(types[0], "177") if types else VIOLATION_SECTION_MAP.get(raw_type, "177")
    return {
        "challan_type": "ONOC_COMPATIBLE_DRAFT",
        "version": "1.0",
        "generated_at": now.isoformat(),
        "challan_number": challan_number_for(evidence_row.evidence_id, now),
        "registration_number": plate,
        "violation_code": violation_type,
        "violation_codes": types,
        "violation_label": violation_label,
        "violation_section": section,
        "fine_amount_inr": fine,
        "payment_due_date": due.strftime("%d %b %Y"),
        "location": {
            "lat": evidence_row.latitude,
            "lng": evidence_row.longitude,
            "camera_id": evidence_row.camera_id,
        },
        "evidence_ref": evidence_row.annotated_path,
        "evidence_id": evidence_row.evidence_id,
        "confidence": evidence_row.confidence,
        "reason": evidence_row.reason,
        "officer_confirmed": evidence_row.review_status == "confirmed",
        "officer_id": officer_id,
        "vehicle_class": evidence_row.vehicle_class,
        "vehicle_id": getattr(evidence_row, "vehicle_id", None),
        "payment_channels": ["e-Challan portal", "Virtual Court", "UPI / Net Banking"],
        "dispute_url": "https://echallan.parivahan.gov.in",
    }


def save_challan_receipt(challan: dict[str, Any], evidence_id: str) -> str:
    """Persist printable receipt HTML alongside enforcement evidence."""
    html_doc = render_receipt_html(challan)
    out = EVIDENCE_DIR / f"{evidence_id}_challan.html"
    out.write_text(html_doc, encoding="utf-8")
    return str(out)


def mask_plate(plate: Optional[str]) -> str:
    if not plate or len(plate) < 4:
        return "****"
    return plate[:2] + "**" + plate[-2:]
