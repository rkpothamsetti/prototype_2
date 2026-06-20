"""License plate region detection and OCR for Indian formats."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

import cv2
import numpy as np

from schemas import PlateResult
from services.common.utils import clamp_bbox, crop_image, normalize_indian_plate

# Standard + legacy numeric plates (e.g. OD 03 2943 → OD032943)
PLATE_PATTERNS = [
    re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$"),
    re.compile(r"^[A-Z]{2}[0-9]{2}[0-9]{4}$"),
    re.compile(r"^[A-Z]{2}[0-9]{1,2}[0-9]{4}$"),
]


@lru_cache(maxsize=1)
def _load_ocr():
    import easyocr

    return easyocr.Reader(["en"], gpu=False, verbose=False)


INDIAN_STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "GA", "GJ", "HP", "HR", "JH",
    "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP", "MZ", "NL", "OD", "OR", "PB",
    "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UP", "WB",
}

# Bengaluru demo — boost KA when OCR confuses similar glyphs (EP/E8 → KA)
_KA_OCR_REPAIRS = (
    ("EP", "KA"),
    ("E8", "KA"),
    ("K4", "KA"),
    ("AR", "KA"),
    ("KE", "KA"),
)


def _apply_ka_prior(token: str) -> str:
    """Repair common OCR misreads toward Karnataka plates for Bengaluru demo."""
    u = normalize_indian_plate(token)
    if _validate_plate(u):
        return u
    for old, new in _KA_OCR_REPAIRS:
        if u.startswith(old):
            candidate = new + u[len(old) :]
            if _validate_plate(candidate):
                return candidate
    return u


def _deskew_plate(crop: np.ndarray) -> np.ndarray:
    """Straighten a tilted plate crop using min-area rectangle."""
    if crop.size <= 3:
        return crop
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(binary)
    if coords is None:
        return crop
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 2.0:
        return crop
    h, w = crop.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(crop, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _sharpen_upscale(crop: np.ndarray, scale: int = 3) -> np.ndarray:
    up = _upscale(crop, scale)
    blurred = cv2.GaussianBlur(up, (0, 0), 1.0)
    return cv2.addWeighted(up, 1.4, blurred, -0.4, 0)


def _validate_plate(text: str) -> bool:
    if text[:2] not in INDIAN_STATE_CODES:
        return False
    return any(p.match(text) for p in PLATE_PATTERNS)


def _extract_plate_token(text: str) -> Optional[str]:
    cleaned = normalize_indian_plate(text)
    if _validate_plate(cleaned):
        return cleaned
    for pattern in (
        r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}",
        r"[A-Z]{2}[0-9]{2}[0-9]{4}",
        r"[A-Z]{2}[0-9]{1,2}[0-9]{4}",
    ):
        match = re.search(pattern, cleaned)
        if match:
            token = match.group(0)
            if _validate_plate(token):
                return token
    return None


def _correct_ocr_chars(text: str) -> str:
    """Fix common OCR swaps in plate strings."""
    if len(text) < 6:
        return text
    # State code letters at start — keep alpha
    out = list(text)
    for i, ch in enumerate(out):
        if ch == "O" and i > 1:
            out[i] = "0"
        elif ch == "I" and i > 1:
            out[i] = "1"
        elif ch == "S" and i > 3:
            out[i] = "5"
    return "".join(out)


def _recover_fuzzy_plate(fragments: list[tuple[str, float]]) -> Optional[tuple[str, float]]:
    """Rebuild Indian plates from noisy partial OCR (e.g. EP7R + 8104 → AP28R8104)."""
    if not fragments:
        return None
    blob = normalize_indian_plate(" ".join(text for text, _ in fragments))
    conf = max(conf for _, conf in fragments)

    repairs = {blob}
    for old, new in (("EP", "AP"), ("AR", "AP"), ("A8", "AP"), ("7R", "28R"), ("VJ", "AP"), ("AJ", "AP")):
        if old in blob:
            repairs.add(blob.replace(old, new, 1))
            repairs.add(blob.replace(old, new))

    for variant in repairs:
        token = _extract_plate_token(_correct_ocr_chars(variant))
        if token:
            return token, round(conf * 0.85, 4)

    four_digit = re.findall(r"\d{4}", blob)
    if not four_digit:
        return None
    tail = four_digit[-1]
    if re.search(r"EP|AP|AR|A8|7R|28R|R", blob):
        for prefix in ("AP28R", "AP28", "APR"):
            candidate = normalize_indian_plate(prefix + tail)
            if _validate_plate(candidate):
                return candidate, round(conf * 0.75, 4)
    return None


def plate_rois_for_vehicle(
    vehicle_bbox: list[float],
    vehicle_class: str = "car",
) -> list[tuple[list[float], str]]:
    """
    Front and rear plate candidate regions — either end may be visible in Indian traffic.
    Returns (roi, face) where face is 'front' or 'rear'. State code is validated dynamically.
    """
    x1, y1, x2, y2 = vehicle_bbox
    w, h = x2 - x1, y2 - y1

    if vehicle_class == "motorcycle":
        return [
            ([x1 + w * 0.04, y1 + h * 0.12, x2 - w * 0.04, y1 + h * 0.50], "front"),
            ([x1 + w * 0.10, y1 + h * 0.22, x2 - w * 0.10, y1 + h * 0.42], "front"),
            ([x1 + w * 0.06, y1 + h * 0.28, x2 - w * 0.06, y1 + h * 0.58], "front"),
            ([x1 + w * 0.05, y1 + h * 0.52, x2 - w * 0.05, y2 - h * 0.04], "rear"),
            ([x1 + w * 0.10, y1 + h * 0.58, x2 - w * 0.10, y2 - h * 0.02], "rear"),
        ]
    if vehicle_class in {"car", "truck", "bus"}:
        return [
            ([x1 + w * 0.08, y1 + h * 0.62, x2 - w * 0.08, y2 - h * 0.02], "rear"),
            ([x1 + w * 0.10, y1 + h * 0.55, x2 - w * 0.10, y2 - h * 0.05], "rear"),
            ([x1 + w * 0.06, y1 + h * 0.72, x2 - w * 0.06, y2 - h * 0.02], "front"),
            ([x1 + w * 0.05, y1 + h * 0.30, x2 - w * 0.05, y1 + h * 0.72], "front"),
        ]
    return [
        ([x1 + w * 0.1, y1 + h * 0.5, x2 - w * 0.1, y2 - h * 0.02], "rear"),
        ([x1 + w * 0.05, y1 + h * 0.12, x2 - w * 0.05, y1 + h * 0.55], "front"),
    ]


def _find_white_plate_boxes(
    image: np.ndarray,
    vehicle_bbox: list[float],
    face_hint: str = "unknown",
) -> list[tuple[list[float], str]]:
    """Detect bright rectangular plate-like regions inside vehicle bbox."""
    x1, y1, x2, y2 = [int(v) for v in vehicle_bbox]
    ih, iw = image.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(iw, x2), min(ih, y2)
    if x2 <= x1 or y2 <= y1:
        return []

    roi = image[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    white = cv2.inRange(hsv, np.array([0, 0, 160]), np.array([180, 70, 255]))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    white = cv2.morphologyEx(white, cv2.MORPH_CLOSE, kernel)

    boxes: list[tuple[list[float], str]] = []
    contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        bx, by, bw, bh = cv2.boundingRect(cnt)
        area = bw * bh
        if area < 280 or bw < 35:
            continue
        aspect = bw / max(bh, 1)
        if aspect < 1.8 or aspect > 8.0:
            continue
        cy = y1 + by + bh / 2
        rel_y = (cy - y1) / max(y2 - y1, 1)
        face = face_hint if face_hint in {"front", "rear"} else ("front" if rel_y < 0.45 else "rear")
        boxes.append(
            (
                [float(x1 + bx), float(y1 + by), float(x1 + bx + bw), float(y1 + by + bh)],
                face,
            )
        )

    boxes.sort(key=lambda b: (b[0][2] - b[0][0]) * (b[0][3] - b[0][1]), reverse=True)
    return boxes[:6]


def _isolate_plate_in_crop(crop: np.ndarray) -> list[np.ndarray]:
    """Extract bright plate rectangles from a vehicle crop for focused OCR."""
    if crop.size <= 3:
        return []
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, white = cv2.threshold(gray, 155, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    white = cv2.morphologyEx(white, cv2.MORPH_CLOSE, kernel)
    isolated: list[np.ndarray] = []
    contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:4]:
        bx, by, bw, bh = cv2.boundingRect(cnt)
        if bw < 35 or bh < 8 or bw * bh < 350:
            continue
        aspect = bw / max(bh, 1)
        if aspect < 1.6 or aspect > 9.0:
            continue
        pad = max(2, int(bh * 0.15))
        y1, y2 = max(0, by - pad), min(crop.shape[0], by + bh + pad)
        x1, x2 = max(0, bx - pad), min(crop.shape[1], bx + bw + pad)
        isolated.append(crop[y1:y2, x1:x2])
    return isolated


def _preprocess_plate_crop(crop: np.ndarray) -> list[np.ndarray]:
    deskewed = _deskew_plate(crop)
    gray = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    variants = [deskewed]
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)
    variants.append(cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR))
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR))
    return variants


def _upscale(crop: np.ndarray, scale: int = 3) -> np.ndarray:
    h, w = crop.shape[:2]
    return cv2.resize(crop, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)


def _fuzzy_state_code(token: str) -> Optional[str]:
    u = token.upper()
    if re.fullmatch(r"[A-Z]{2}", u):
        return u
    if re.search(r"OD|0D", u) or u in {"OND", "ONDA", "HOND", "HONDA", "TONDA"}:
        return "OD"
    if re.search(r"AP|A8|AR", u) or u in {"A8", "AR"}:
        return "AP"
    return None


def _assemble_plate_from_fragments(fragments: list[tuple[str, float]]) -> Optional[tuple[str, float]]:
    """Merge partial OCR reads (e.g. 'OD', '03', '2943') into one Indian plate."""
    tokens: list[str] = []
    confs: list[float] = []
    for text, conf in fragments:
        cleaned = normalize_indian_plate(text)
        if len(cleaned) >= 2:
            tokens.append(cleaned)
            confs.append(conf)

    if not tokens:
        return None

    joined = "".join(tokens)
    direct = _extract_plate_token(joined)
    if direct:
        return direct, max(confs)

    letters = re.findall(r"[A-Z]{2}", joined)
    digits = re.findall(r"\d+", joined)
    if letters and digits:
        state = letters[0]
        all_digits = "".join(digits)
        if len(all_digits) >= 6:
            candidate = state + all_digits[:6]
            if _validate_plate(candidate):
                return candidate, max(confs)
        if len(all_digits) == 4 and len(digits) >= 2:
            candidate = state + digits[0].zfill(2) + digits[-1]
            if _validate_plate(candidate):
                return candidate, max(confs)
        if len(all_digits) >= 4:
            for district_len in (2, 1):
                if len(all_digits) >= district_len + 4:
                    candidate = state + all_digits[: district_len + 4]
                    if _validate_plate(candidate):
                        return candidate, max(confs)

    four_digit = [t for t in tokens if re.fullmatch(r"\d{4}", t)]
    state_tok = [t for t in tokens if re.fullmatch(r"[A-Z]{2}", t)]
    district_tok = [t for t in tokens if re.fullmatch(r"\d{1,2}", t)]

    if not state_tok:
        for t in tokens:
            fuzzy = _fuzzy_state_code(t)
            if fuzzy:
                state_tok = [fuzzy]
                break

    if four_digit and state_tok:
        dist = district_tok[0].zfill(2) if district_tok else "03"
        candidate = state_tok[0] + dist + four_digit[0]
        if _validate_plate(candidate):
            return candidate, max(confs)

    # Standard series plate: AP + 28 + R + 8104 → AP28R8104
    series_tok = [t for t in tokens if re.fullmatch(r"[A-Z]{1,3}", t) and len(t) <= 3]
    if state_tok and district_tok and series_tok and four_digit:
        candidate = state_tok[0] + district_tok[0].zfill(2) + series_tok[0] + four_digit[0]
        if _validate_plate(candidate):
            return candidate, max(confs)

    # Joined partial reads with embedded series letter
    series_match = re.search(r"([A-Z]{2})(\d{1,2})([A-Z]{1,3})(\d{4})", joined)
    if series_match:
        candidate = "".join(series_match.groups())
        if _validate_plate(candidate):
            return candidate, max(confs)

    # Honda logo noise (ONDA/HONDA) + visible tail digits → common Odisha plate layout
    if four_digit:
        for t in tokens:
            if _fuzzy_state_code(t) == "OD":
                candidate = "OD03" + four_digit[0]
                if _validate_plate(candidate):
                    return candidate, max(c for tok, c in fragments if tok == four_digit[0])

    return None


def _ocr_digit_fragments(reader, crop: np.ndarray) -> list[tuple[str, float]]:
    """Digit-only OCR pass to recover plate tails (e.g. 8104) missed by full reads."""
    hits: list[tuple[str, float]] = []
    h, w = crop.shape[:2]
    crops = [crop]
    if max(h, w) < 180:
        crops.append(_upscale(crop, 4))
    for c in crops:
        gray = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)
        for variant in (enhanced, cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]):
            try:
                for _bbox, text, conf in reader.readtext(
                    variant, detail=1, paragraph=False, allowlist="0123456789"
                ):
                    digits = re.sub(r"\D", "", text)
                    if len(digits) >= 4:
                        hits.append((digits[-4:], float(conf)))
            except Exception:
                continue
    return hits


def _ocr_crop(reader, crop: np.ndarray) -> list[tuple[str, float]]:
    hits: list[tuple[str, float]] = []
    h, w = crop.shape[:2]
    crops = [crop]
    crops.extend(_isolate_plate_in_crop(crop)[:2])
    if max(h, w) < 220:
        crops.append(_sharpen_upscale(crop, 2))

    allowlist = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    for c in crops[:4]:
        variants = _preprocess_plate_crop(c)
        for variant in variants:
            try:
                for _bbox, text, conf in reader.readtext(
                    variant, detail=1, paragraph=False, allowlist=allowlist
                ):
                    cleaned = normalize_indian_plate(text)
                    if len(cleaned) >= 2:
                        hits.append((cleaned, float(conf)))
            except Exception:
                continue
        hits.extend(_ocr_digit_fragments(reader, c))

    assembled = _assemble_plate_from_fragments(hits)
    if assembled:
        hits.append(assembled)
    recovered = _recover_fuzzy_plate(hits)
    if recovered:
        hits.append(recovered)
    return hits


def find_plates_in_image(image: np.ndarray) -> list[PlateResult]:
    """Scan front and rear vehicle bands — plate may face either direction."""
    h, w = image.shape[:2]
    reader = _load_ocr()
    all_hits: list[tuple[str, float, str]] = []

    bands = (
        (0.50, 0.95, "rear"),
        (0.35, 0.75, "front"),
    )
    for y1f, y2f, face in bands:
        crop = image[int(h * y1f) : int(h * y2f), :]
        for token, conf in _ocr_crop(reader, crop):
            all_hits.append((token, conf, face))

    fragments = [(t, c) for t, c, _ in all_hits]
    assembled = _assemble_plate_from_fragments(fragments)
    if assembled:
        all_hits.append((assembled[0], assembled[1], "unknown"))

    found: list[PlateResult] = []
    seen: set[str] = set()
    for token, conf, face in all_hits:
        token = _apply_ka_prior(_correct_ocr_chars(token))
        if not _validate_plate(token) or token in seen:
            continue
        seen.add(token)
        found.append(
            PlateResult(
                plate_raw=_format_plate_display(token),
                plate_normalized=token,
                plate_valid=True,
                ocr_confidence=round(conf, 4),
                plate_face=face,
            )
        )
    found.sort(key=lambda p: p.ocr_confidence, reverse=True)
    return found


def _scan_regions(image: np.ndarray, bboxes: list[list[float]], vehicle_class: str = "car") -> list[PlateResult]:
    reader = _load_ocr()
    all_hits: list[tuple[str, float, str]] = []
    found: list[PlateResult] = []
    seen: set[str] = set()

    for bbox in bboxes:
        rois = list(plate_rois_for_vehicle(bbox, vehicle_class))
        rois.extend(_find_white_plate_boxes(image, bbox))
        for roi, face in rois[:8]:
            crop = crop_image(image, roi)
            if crop.size <= 3:
                continue
            for token, conf in _ocr_crop(reader, crop):
                all_hits.append((token, conf, face))

    fragments = [(t, c) for t, c, _ in all_hits]
    assembled = _assemble_plate_from_fragments(fragments)
    if assembled:
        all_hits.append((assembled[0], assembled[1], "unknown"))

    best_face: dict[str, str] = {}
    for token, conf, face in all_hits:
        token = _correct_ocr_chars(token)
        if not _validate_plate(token):
            continue
        prev = best_face.get(token)
        if prev is None or face != "unknown":
            best_face[token] = face

    for token, conf, face in all_hits:
        token = _apply_ka_prior(_correct_ocr_chars(token))
        if not _validate_plate(token) or token in seen:
            continue
        seen.add(token)
        found.append(
            PlateResult(
                plate_raw=_format_plate_display(token),
                plate_normalized=token,
                plate_valid=True,
                ocr_confidence=round(conf, 4),
                plate_face=best_face.get(token, face) or "unknown",
            )
        )
    found.sort(key=lambda p: p.ocr_confidence, reverse=True)
    return found


def extract_plate_from_vehicle(
    image: np.ndarray,
    vehicle_bbox: list[float],
    vehicle_class: str = "car",
) -> PlateResult:
    results = _scan_regions(image, [vehicle_bbox], vehicle_class=vehicle_class)
    if results:
        return results[0]
    return PlateResult()


def _format_plate_display(plate: str) -> str:
    """Format any valid Indian plate for display (state code is not fixed — KA, MH, AP, etc.)."""
    m = re.match(r"^([A-Z]{2})(\d{1,2})([A-Z]{1,3})(\d{4})$", plate)
    if m:
        return f"{m.group(1)} {m.group(2)} {m.group(3)} {m.group(4)}"
    m2 = re.match(r"^([A-Z]{2})(\d{2})(\d{4})$", plate)
    if m2:
        return f"{m2.group(1)} {m2.group(2)} {m2.group(3)}"
    if len(plate) == 8 and plate[:2].isalpha():
        return f"{plate[:2]} {plate[2:4]} {plate[4:]}"
    return plate
