"""Tests for helmet and plate improvements."""
from pathlib import Path

import numpy as np
import cv2

from services.violation_reasoning.helmet import helmet_presence_score
from services.ocr.service import _apply_ka_prior, _extract_plate_token, _validate_plate


def test_ka_prior_repair():
    assert _apply_ka_prior("EP01AB1234") == "KA01AB1234"
    assert _validate_plate(_apply_ka_prior("KA03MA5678"))


def test_helmet_open_visor_black_shell():
    """Black helmet shell on top + skin face in center → helmet present."""
    img = np.full((120, 100, 3), 180, dtype=np.uint8)
    cv2.rectangle(img, (10, 5), (90, 55), (25, 25, 25), -1)  # black crown
    cv2.rectangle(img, (5, 30), (20, 90), (30, 30, 30), -1)
    cv2.rectangle(img, (80, 30), (95, 90), (30, 30, 30), -1)
    cv2.ellipse(img, (50, 65), (22, 28), 0, 0, 360, (170, 140, 120), -1)  # face
    score = helmet_presence_score(img, [0, 0, 100, 120])
    assert score >= 0.55, f"expected helmet detected, got {score}"


def test_helmet_bare_head():
    """Skin-only head without dark shell → no helmet."""
    img = np.full((100, 80, 3), 200, dtype=np.uint8)
    cv2.ellipse(img, (40, 50), (25, 35), 0, 0, 360, (180, 150, 130), -1)
    score = helmet_presence_score(img, [0, 0, 80, 100])
    assert score < 0.42, f"expected no helmet, got {score}"


def test_plate_od_format():
    assert _validate_plate("OD032943")
    token = _extract_plate_token("OD 03 2943")
    assert token == "OD032943"


def test_veh002_stacked_rider_no_helmet():
    """Regression: adult + child on bike — cloth cap must not mask bare adult head."""
    from pathlib import Path
    from schemas import SceneConfig
    from services.detection.service import detect_objects
    from services.preprocessing.service import preprocess_frame
    from services.violation_reasoning.service import evaluate_violations

    img_path = Path(__file__).resolve().parents[1] / "data/uploads/1439f008-34c5-405f-a53a-12dbbac0d92a.jpg"
    if not img_path.exists():
        return
    raw = cv2.imread(str(img_path))
    proc, meta = preprocess_frame(raw)
    viols, vehicles, _ = evaluate_violations(
        proc, detect_objects(proc), meta, SceneConfig(), source_image=raw
    )
    moto = next((v for v in vehicles if v.vehicle_id == "VEH-002"), None)
    assert moto is not None
    helmet_v = [v for v in viols if v.vehicle_id == "VEH-002" and v.violation_type == "helmet_non_compliance"]
    assert helmet_v, "VEH-002 should be helmet non-compliant (adult bare head)"
    assert not moto.associated_persons[0].helmet_detected


def test_cloth_cap_scores_low():
    """Blue knit cap should not score as safety helmet."""
    img = np.full((120, 100, 3), 200, dtype=np.uint8)
    cv2.rectangle(img, (15, 5), (85, 55), (180, 90, 40), -1)  # blue cap
    cv2.ellipse(img, (50, 75), (22, 28), 0, 0, 360, (170, 140, 120), -1)  # face below
    score = helmet_presence_score(img, [0, 0, 100, 120])
    assert score < 0.42, f"cloth cap should not read as helmet, got {score}"


def test_helmet_bare_head_after_preprocessing():
    """CLAHE preprocessing must not turn dark hair into a false helmet."""
    from services.preprocessing.service import preprocess_image
    from services.detection.service import detect_objects
    from services.violation_reasoning.service import evaluate_violations
    from schemas import SceneConfig

    img_path = Path(__file__).resolve().parents[1] / (
        ".cursor/projects/c-Users-krish-OneDrive-Desktop-flipkart-gridlock-cursor/assets/"
        "c__Users_krish_AppData_Roaming_Cursor_User_workspaceStorage_55551b5c99b0a72d6e0b908eb4969557_images_image-c3df0149-634b-45e8-8b26-21ee1d5049eb.png"
    )
    if not img_path.exists():
        return
    raw = cv2.imread(str(img_path))
    image, meta, _ = preprocess_image(raw, "helmet-regression")
    viols, vehicles, _ = evaluate_violations(
        image, detect_objects(image), meta, SceneConfig(), source_image=raw
    )
    helmet_violations = [v for v in viols if v.violation_type == "helmet_non_compliance"]
    assert helmet_violations, "expected helmet violation on bare-headed rider"
    assert not vehicles[0].associated_persons[0].helmet_detected

    from services.ocr.service import _format_plate_display, plate_rois_for_vehicle

    for plate in ("AP28R8104", "KA01AB1234", "MH12DE1433", "TN09BX5678"):
        assert _validate_plate(plate), plate
        display = _format_plate_display(plate)
        assert display.startswith(plate[:2])

    rois = plate_rois_for_vehicle([0, 0, 200, 400], "motorcycle")
    faces = {f for _, f in rois}
    assert "front" in faces and "rear" in faces
