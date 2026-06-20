"""Generate synthetic demo traffic images for evaluation."""
from pathlib import Path

import cv2
import numpy as np

OUT_DIR = Path(__file__).resolve().parent.parent / "CONTEXT" / "examples" / "sample_input"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _save(name: str, image: np.ndarray) -> None:
    cv2.imwrite(str(OUT_DIR / name), image)


def generate_samples() -> None:
    # OpenCV uses BGR — (B, G, R)
    RED_CAR = (40, 40, 220)
    BLUE_BIKE = (220, 80, 40)
    SKIN = (140, 180, 210)

    # Motorcycle with rider (helmet violation candidate)
    img = np.full((720, 1280, 3), 60, dtype=np.uint8)
    cv2.rectangle(img, (500, 350), (780, 620), BLUE_BIKE, -1)
    cv2.circle(img, (620, 320), 35, SKIN, -1)
    _save("motorcycle_rider.jpg", img)

    # Triple riding - 3 persons on bike
    img2 = np.full((720, 1280, 3), 80, dtype=np.uint8)
    cv2.rectangle(img2, (450, 380), (750, 600), BLUE_BIKE, -1)
    for x in (520, 600, 680):
        cv2.circle(img2, (x, 340), 28, SKIN, -1)
    _save("triple_riding.jpg", img2)

    # Parked car in no-parking zone
    img3 = np.full((720, 1280, 3), 90, dtype=np.uint8)
    cv2.rectangle(img3, (100, 300), (500, 600), RED_CAR, -1)
    cv2.putText(img3, "NO PARKING", (120, 280), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    _save("illegal_parking.jpg", img3)

    # Car with plate region
    img4 = np.full((720, 1280, 3), 100, dtype=np.uint8)
    cv2.rectangle(img4, (400, 250), (900, 550), RED_CAR, -1)
    cv2.rectangle(img4, (580, 480), (720, 520), (255, 255, 255), -1)
    cv2.putText(img4, "KA 01 AB 1234", (592, 512), cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 0, 0), 2, cv2.LINE_AA)
    _save("car_with_plate.jpg", img4)

    print(f"Generated samples in {OUT_DIR}")


if __name__ == "__main__":
    generate_samples()
