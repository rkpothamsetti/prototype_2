"""Evaluate TrafficVision on labeled examples."""
from __future__ import annotations

import json
import time
from pathlib import Path

import cv2

from schemas import SceneConfig
from services.common.utils import iou
from services.detection.service import detect_objects
from services.preprocessing.service import preprocess_image
from services.violation_reasoning.service import evaluate_violations

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "CONTEXT" / "examples" / "sample_input"
EXPECTED_DIR = ROOT / "CONTEXT" / "examples" / "expected_output"


def detection_map(predictions: list, ground_truth: list, iou_thresh: float = 0.5) -> dict:
    tp = 0
    matched = set()
    for gt in ground_truth:
        for idx, pred in enumerate(predictions):
            if idx in matched:
                continue
            if pred.class_name == gt["class"] and iou(pred.bbox, gt["bbox"]) >= iou_thresh:
                tp += 1
                matched.add(idx)
                break
    fp = len(predictions) - len(matched)
    fn = len(ground_truth) - tp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def main() -> None:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)

    if not any(SAMPLES.glob("*.jpg")):
        from scripts.generate_samples import generate_samples

        generate_samples()

    latencies: list[float] = []
    det_scores: list[dict] = []

    for image_path in sorted(SAMPLES.glob("*.jpg")):
        image = cv2.imread(str(image_path))
        start = time.perf_counter()
        processed, meta, _ = preprocess_image(image, image_path.stem)
        detections = detect_objects(processed)
        violations, vehicles, _derived = evaluate_violations(processed, detections, meta, SceneConfig())
        latencies.append((time.perf_counter() - start) * 1000)

        expected_path = EXPECTED_DIR / f"{image_path.stem}.json"
        if expected_path.exists():
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            gt = expected.get("detections", [])
            det_scores.append(detection_map(detections, gt))

        print(f"{image_path.name}: {len(detections)} detections, {len(violations)} violations")

    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0

    if det_scores:
        avg_p = sum(s["precision"] for s in det_scores) / len(det_scores)
        avg_r = sum(s["recall"] for s in det_scores) / len(det_scores)
        avg_f1 = sum(s["f1"] for s in det_scores) / len(det_scores)
    else:
        avg_p = avg_r = avg_f1 = 0.0

    report = {
        "samples": len(latencies),
        "detection_precision_avg": round(avg_p, 4),
        "detection_recall_avg": round(avg_r, 4),
        "detection_f1_avg": round(avg_f1, 4),
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
    }
    print("\n=== Evaluation Report ===")
    print(json.dumps(report, indent=2))

    out = ROOT / "data" / "evaluation_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
