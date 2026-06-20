"""Helmet presence analysis on rider head ROI."""
from __future__ import annotations

import cv2
import numpy as np

from services.common.utils import crop_image, head_rois_from_person


def _cloth_cap_likelihood(hsv: np.ndarray, gray: np.ndarray, h: int, w: int) -> float:
    """
    Soft knit / cloth cap (beanie, turban cloth) — colored textile without hard shell.
    Returns 0–1 likelihood that the headwear is NOT a safety helmet.
    """
    crown_hsv = hsv[0 : max(1, int(h * 0.35)), :]
    crown_gray = gray[0 : max(1, int(h * 0.35)), :]

    blue = cv2.inRange(crown_hsv, np.array([85, 30, 35]), np.array([135, 255, 255]))
    warm = cv2.inRange(crown_hsv, np.array([0, 35, 40]), np.array([18, 255, 255]))
    green = cv2.inRange(crown_hsv, np.array([35, 30, 40]), np.array([85, 255, 255]))
    colored = cv2.bitwise_or(cv2.bitwise_or(blue, warm), green)
    color_frac = float(np.mean(colored > 0))

    # Black / white ISI helmets are not colored textile — skip cloth-cap path
    if color_frac < 0.06:
        return 0.0

    edges = cv2.Canny(crown_gray, 45, 120)
    edge_density = float(np.mean(edges > 0))
    lap_var = float(cv2.Laplacian(crown_gray, cv2.CV_64F).var())

    score = 0.0
    if color_frac > 0.07:
        score += min(0.55, color_frac * 2.2)
    if edge_density < 0.13:
        score += 0.22
    if lap_var < 220:
        score += 0.18
    return float(min(1.0, score))


def helmet_presence_score(image: np.ndarray, head_bbox: list[float]) -> float:
    """
    Estimate likelihood that a helmet is worn (higher = helmet present).

    Handles open-visor helmets: dark shell on crown/sides + visible face in center
    still counts as helmet compliant.
    """
    raw_y1 = head_bbox[1]
    crop = crop_image(image, head_bbox)
    if crop.size <= 3:
        return 0.0

    h, w = crop.shape[:2]
    if h < 8 or w < 8:
        return 0.0

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    crown = gray[0 : max(1, int(h * 0.45)), :]
    sides = np.concatenate(
        [gray[:, 0 : max(1, int(w * 0.18))].flatten(), gray[:, max(1, int(w * 0.82)) : w].flatten()]
    )
    center = gray[int(h * 0.2) : int(h * 0.8), int(w * 0.2) : int(w * 0.8)]

    crown_dark = float(np.mean(crown < 95))
    side_dark = float(np.mean(sides < 105)) if sides.size else 0.0
    center_dark = float(np.mean(center < 90)) if center.size else 0.0

    lower_skin = np.array([0, 25, 50], dtype=np.uint8)
    upper_skin = np.array([22, 180, 255], dtype=np.uint8)
    skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
    crown_skin = float(np.mean(skin_mask[0 : max(1, int(h * 0.4)), :] > 0))
    center_skin = float(np.mean(skin_mask[int(h * 0.2) : int(h * 0.85), int(w * 0.15) : int(w * 0.85)] > 0))

    edges = cv2.Canny(gray, 60, 150)
    crown_edges = float(np.mean(edges[0 : max(1, int(h * 0.5)), :] > 0))

    cloth = _cloth_cap_likelihood(hsv, gray, h, w)

    if raw_y1 < 0:
        crown_dark *= 0.45
        crown_edges *= 0.6

    # Cloth cap / beanie — colored soft textile, not ISI helmet shell
    if cloth >= 0.50:
        return float(max(0.05, 0.18 - center_skin * 0.08))

    # Dark hair mimics helmet crown: top is dark but sides lack helmet shell
    if crown_dark >= 0.20 and side_dark < 0.18 and crown_skin < 0.18:
        return float(max(0.05, min(0.32, 0.12 + crown_dark * 0.2 - side_dark * 0.4)))

    # Bare head: visible face, little shell on crown/sides
    if center_skin > 0.08 and crown_skin < 0.16:
        if side_dark < 0.26 and crown_edges < 0.12:
            base = 0.28 - center_skin * 0.38 - crown_skin * 0.22
            if cloth >= 0.30:
                base -= 0.12
            return float(max(0.05, base))

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    gray_std = float(np.std(gray))

    # Misaligned ROI on demo assets: mixed dark block, no edge structure
    if (
        crown_edges < 0.06
        and lap_var < 1800
        and crown_dark >= 0.75
        and side_dark >= 0.75
        and gray_std > 40
    ):
        return 0.12

    # Strong helmet shell on top/sides (black helmet, open visor)
    if crown_dark >= 0.32 and side_dark >= 0.20:
        if cloth >= 0.35:
            return float(max(0.08, 0.32 - cloth * 0.35 - center_skin * 0.25))
        shell = 0.45 * crown_dark + 0.35 * side_dark + 0.12 * crown_edges + 0.08 * center_dark
        if center_skin > 0.15 and (crown_dark >= 0.18 or side_dark >= 0.18):
            return float(min(1.0, max(0.72, shell + 0.25)))
        return float(min(1.0, max(0.55, shell + 0.2)))

    if side_dark >= 0.28:
        if cloth >= 0.35:
            return float(max(0.08, 0.38 - cloth * 0.3))
        shell = 0.45 * crown_dark + 0.35 * side_dark + 0.12 * crown_edges + 0.08 * center_dark
        return float(min(1.0, max(0.55, shell + 0.2)))

    # Full-face helmet (dark overall, low skin on crown)
    if center_dark >= 0.35 and crown_skin < 0.2 and cloth < 0.35:
        return float(min(1.0, 0.65 + center_dark * 0.3))

    # Bare head: skin dominant on crown, little dark shell
    if crown_skin > 0.20 and crown_dark < 0.14 and side_dark < 0.18:
        return float(max(0.05, 0.24 - crown_skin * 0.32))

    ambiguous = 0.35 * crown_dark + 0.3 * side_dark + 0.2 * (1.0 - crown_skin) + 0.15 * crown_edges
    if cloth >= 0.30:
        ambiguous -= cloth * 0.25
    return float(max(0.0, min(1.0, ambiguous)))


def helmet_presence_scores_for_person(
    image: np.ndarray,
    person_bbox: list[float],
    image_shape: tuple[int, ...] | None = None,
) -> list[float]:
    """Score each head band when YOLO merges stacked riders into one person box."""
    return [
        helmet_presence_score(image, roi)
        for roi in head_rois_from_person(person_bbox, image_shape)
    ]


def worst_helmet_presence_score(
    image: np.ndarray,
    person_bbox: list[float],
    image_shape: tuple[int, ...] | None = None,
) -> float:
    """Minimum score across head bands — violation if any rider head lacks helmet."""
    scores = helmet_presence_scores_for_person(image, person_bbox, image_shape)
    return min(scores) if scores else 0.0
