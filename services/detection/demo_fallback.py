"""Contour-based fallback detections for synthetic demo images when YOLO finds nothing."""
from __future__ import annotations

import uuid

import cv2
import numpy as np

from schemas import Detection


def demo_contour_detection(image: np.ndarray) -> list[Detection]:
    detections: list[Detection] = []
    h, w = image.shape[:2]

    vehicle_mask = _vehicle_color_mask(image)
    contours, _ = cv2.findContours(vehicle_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    vehicle_boxes: list[list[float]] = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 8000:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < 80 or bh < 80:
            continue
        vehicle_boxes.append([float(x), float(y), float(x + bw), float(y + bh)])

    persons = _detect_person_circles(image)

    for bbox in vehicle_boxes:
        vclass = _classify_vehicle(image, bbox, persons)
        detections.append(
            Detection(
                track_id=str(uuid.uuid4()),
                class_name=vclass,
                bbox=bbox,
                confidence=0.78,
            )
        )

    detections.extend(persons)
    return _tag_riders(detections)


def _classify_vehicle(image: np.ndarray, bbox: list[float], persons: list[Detection]) -> str:
    x1, y1, x2, y2 = [int(v) for v in bbox]
    roi = image[y1:y2, x1:x2]
    mean_bgr = roi.mean(axis=(0, 1))
    b, g, r = float(mean_bgr[0]), float(mean_bgr[1]), float(mean_bgr[2])

    riders_above = 0
    for p in persons:
        pcx = (p.bbox[0] + p.bbox[2]) / 2
        pcy = (p.bbox[1] + p.bbox[3]) / 2
        if y1 - 80 <= pcy <= y1 + 40 and x1 <= pcx <= x2:
            riders_above += 1

    if riders_above >= 1:
        return "motorcycle"
    if r > b + 25 and r > g + 15:
        return "car"
    if b > r + 25 and b > g + 10:
        return "motorcycle"
    return "car"


def _detect_person_circles(image: np.ndarray) -> list[Detection]:
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=40,
        param1=50,
        param2=25,
        minRadius=18,
        maxRadius=45,
    )
    detections: list[Detection] = []
    if circles is None:
        return _skin_blob_persons(image)

    for circle in circles[0]:
        cx, cy, r = circle
        # Ignore white plate / text blobs in lower vehicle area
        if cy > h * 0.55 and r < 40:
            continue
        bbox = [float(cx - r), float(cy - r), float(cx + r), float(cy + r)]
        detections.append(
            Detection(
                track_id=str(uuid.uuid4()),
                class_name="person",
                bbox=bbox,
                confidence=0.72,
            )
        )
    return detections


def _skin_blob_persons(image: np.ndarray) -> list[Detection]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([0, 30, 60]), np.array([25, 180, 255]))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detections: list[Detection] = []
    h, w = image.shape[:2]
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 1200 or area > 8000:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw > 80 or bh > 80:
            continue
        detections.append(
            Detection(
                track_id=str(uuid.uuid4()),
                class_name="person",
                bbox=[float(x), float(y), float(x + bw), float(y + bh)],
                confidence=0.68,
            )
        )
    return detections


def _vehicle_color_mask(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    red1 = cv2.inRange(hsv, np.array([0, 80, 60]), np.array([15, 255, 255]))
    red2 = cv2.inRange(hsv, np.array([160, 80, 60]), np.array([180, 255, 255]))
    blue = cv2.inRange(hsv, np.array([90, 60, 40]), np.array([140, 255, 255]))
    mask = cv2.bitwise_or(red1, red2)
    mask = cv2.bitwise_or(mask, blue)
    kernel = np.ones((5, 5), np.uint8)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


def _tag_riders(detections: list[Detection]) -> list[Detection]:
    from services.common.utils import iou

    bikes = [d for d in detections if d.class_name == "motorcycle"]
    persons = [d for d in detections if d.class_name == "person"]
    for person in persons:
        for bike in bikes:
            if iou(person.bbox, bike.bbox) >= 0.02:
                person.role = "rider"
            else:
                pcx = (person.bbox[0] + person.bbox[2]) / 2
                pcy = (person.bbox[1] + person.bbox[3]) / 2
                if bike.bbox[0] <= pcx <= bike.bbox[2] and person.bbox[3] <= bike.bbox[1] + 50:
                    person.role = "rider"
    return detections
