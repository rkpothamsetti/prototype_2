"""Tests for review tiers and challan export."""
from services.challan.export import build_challan_export, mask_plate, save_challan_receipt
from services.challan.penalties import VIOLATION_PENALTY_INR, penalty_for_violation
from services.challan.receipt import render_receipt_html
from services.review.tiers import classify_review_tier


def test_review_tier_auto_clear():
    status, tier = classify_review_tier(0.3)
    assert status == "auto_cleared"
    assert tier == "low"


def test_review_tier_fast_track():
    status, tier = classify_review_tier(0.85)
    assert status == "pending_review"
    assert tier == "fast_track"


def test_review_tier_standard():
    status, tier = classify_review_tier(0.6)
    assert status == "pending_review"
    assert tier == "standard"


def test_mask_plate():
    assert mask_plate("KA01AB1234") == "KA**34"
    assert mask_plate("") == "****"


class _FakeEvidence:
    evidence_id = "ev-1"
    plate_normalized = "KA01AB1234"
    violation_type = "helmet_non_compliance"
    latitude = 12.97
    longitude = 77.59
    camera_id = "CAM_BLR_MG_01"
    annotated_path = "/tmp/x.jpg"
    confidence = 0.82
    reason = "test"
    review_status = "confirmed"
    vehicle_class = "motorcycle"
    vehicle_id = "VEH-001"


def test_challan_export_shape():
    challan = build_challan_export(_FakeEvidence(), officer_id="OFF-1")
    assert challan["challan_type"] == "ONOC_COMPATIBLE_DRAFT"
    assert challan["registration_number"] == "KA01AB1234"
    assert challan["violation_section"] == "194D"
    assert challan["fine_amount_inr"] == 1000
    assert challan["challan_number"].startswith("ECH")
    assert challan["officer_confirmed"] is True


def test_challan_export_multi_violation_fine():
    row = _FakeEvidence()
    row.violation_type = "helmet_non_compliance,triple_riding"
    challan = build_challan_export(row, officer_id="OFF-1")
    assert challan["fine_amount_inr"] == 3000
    assert "Riding without" in challan["violation_label"] or "Helmet" in challan["violation_label"]
    assert "Triple riding" in challan["violation_label"]


def test_violation_penalties_differ():
    amounts = set(VIOLATION_PENALTY_INR.values())
    assert len(amounts) >= 5
    assert penalty_for_violation("red_light_violation") == 5000
    assert penalty_for_violation("illegal_parking") == 500
    assert penalty_for_violation("wrong_side_driving") == 3000


def test_challan_receipt_html(tmp_path, monkeypatch):
    import services.challan.export as export_mod

    monkeypatch.setattr(export_mod, "EVIDENCE_DIR", tmp_path)
    challan = build_challan_export(_FakeEvidence(), officer_id="OFF-1")
    html_doc = render_receipt_html(challan)
    assert "E-CHALLAN RECEIPT" in html_doc
    assert "KA01AB1234" in html_doc
    assert "₹ 1,000" in html_doc
    assert "data:image/png;base64," in html_doc
    path = save_challan_receipt(challan, "ev-1")
    assert path.endswith("_challan.html")
    assert (tmp_path / "ev-1_challan.html").exists()
