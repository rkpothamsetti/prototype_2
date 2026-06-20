"""Generate hero demo images with clear Bengaluru (KA) license plates for pitch demos."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "demo_hero"

ROAD = (55, 55, 55)
SKY = (180, 200, 220)
RED_CAR = (40, 40, 220)
BLUE_BIKE = (220, 80, 40)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKIN = (140, 180, 210)


def _base_road(w: int = 1280, h: int = 720) -> np.ndarray:
    """Uniform gray canvas — matches sample_input so demo contour detection works."""
    return np.full((h, w, 3), 60, dtype=np.uint8)


def _draw_plate(img: np.ndarray, x1: int, y1: int, x2: int, y2: int, text: str) -> None:
    cv2.rectangle(img, (x1, y1), (x2, y2), WHITE, -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (30, 30, 30), 3)
    font = cv2.FONT_HERSHEY_DUPLEX
    scale = 1.1 if len(text) <= 10 else 0.9
    thickness = 3
    display = text
    if len(text) == 10 and text[:2].isalpha():
        display = f"{text[:2]} {text[2:4]} {text[4:6]} {text[6:]}"
    (tw, th), _ = cv2.getTextSize(display, font, scale, thickness)
    tx = x1 + max(6, ((x2 - x1) - tw) // 2)
    ty = y1 + ((y2 - y1) + th) // 2
    cv2.putText(img, display, (tx, ty), font, scale, BLACK, thickness, cv2.LINE_AA)


def _save(name: str, image: np.ndarray) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    cv2.imwrite(str(path), image)
    return path


def generate_hero_images() -> list[Path]:
    """Create synthetic Bengaluru traffic scenes with readable KA plates."""
    paths: list[Path] = []

    # 1. Car at MG Road with clear rear plate
    img = _base_road()
    cv2.rectangle(img, (380, 280), (900, 580), RED_CAR, -1)
    _draw_plate(img, 560, 500, 760, 560, "KA01AB1234")
    paths.append(_save("ka_car_mg_road.jpg", img))

    # 2. Motorcycle rider — helmet violation candidate
    img2 = _base_road()
    cv2.rectangle(img2, (480, 340), (780, 620), BLUE_BIKE, -1)
    cv2.circle(img2, (620, 290), 38, SKIN, -1)
    _draw_plate(img2, 530, 560, 720, 610, "KA03MA5678")
    paths.append(_save("ka_bike_no_helmet.jpg", img2))

    # 3. Triple riding — 3 riders on one bike
    img3 = _base_road()
    cv2.rectangle(img3, (420, 360), (760, 610), BLUE_BIKE, -1)
    for x in (500, 590, 680):
        cv2.circle(img3, (x, 310), 30, SKIN, -1)
    _draw_plate(img3, 480, 555, 690, 605, "KA05HT9012")
    paths.append(_save("ka_triple_riding.jpg", img3))

    # 4. Car wrong-side (facing camera, plate visible)
    img4 = _base_road()
    cv2.rectangle(img4, (350, 260), (850, 540), (50, 120, 50), -1)
    _draw_plate(img4, 520, 470, 710, 520, "KA02CD3456")
    paths.append(_save("ka_car_plate_clear.jpg", img4))

    # 5. Illegal parking in marked zone
    img5 = _base_road()
    cv2.rectangle(img5, (120, 320), (480, 580), RED_CAR, -1)
    cv2.putText(img5, "NO PARKING", (140, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
    _draw_plate(img5, 220, 520, 410, 570, "KA04EF7890")
    paths.append(_save("ka_illegal_parking.jpg", img5))

    return paths


def main() -> None:
    paths = generate_hero_images()
    print(f"Generated {len(paths)} hero images in {OUT_DIR}")
    for p in paths:
        print(f"  - {p.name}")


if __name__ == "__main__":
    main()
