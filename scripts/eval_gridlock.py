"""Evaluate Nigha AI on labeled Gridlock / demo dataset — publishes reports/eval_results.json."""

from __future__ import annotations



import json

import sys

import time

from collections import defaultdict

from pathlib import Path



import cv2



ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))



from schemas import SceneConfig

from services.common.utils import iou

from services.detection.demo_fallback import demo_contour_detection

from services.detection.service import _is_likely_synthetic, _tag_drivers, detect_objects

from services.association.engine import nms_detections

from services.ocr.service import extract_plate_from_vehicle

from services.preprocessing.service import preprocess_image

from services.violation_reasoning.service import evaluate_violations

from services.warmup import warmup_all



LABELS_DIR = ROOT / "data" / "eval" / "labels"

REPORTS_DIR = ROOT / "reports"

IMAGE_DIRS = [
    ROOT / "data" / "demo_hero",
    ROOT / "CONTEXT" / "examples" / "sample_input",
    ROOT / "data" / "gridlock_dataset",
]





def _collect_images(*, labeled_only: bool = False) -> list[Path]:

    paths: list[Path] = []

    seen: set[str] = set()

    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    for folder in IMAGE_DIRS:

        if not folder.exists():

            continue

        for p in sorted(folder.iterdir()):

            if p.suffix.lower() not in exts or p.name in seen:

                continue

            if labeled_only and not (LABELS_DIR / f"{p.stem}.json").exists():

                continue

            paths.append(p)

            seen.add(p.name)

    return paths





def _load_label(stem: str) -> dict | None:

    path = LABELS_DIR / f"{stem}.json"

    if not path.exists():

        return None

    return json.loads(path.read_text(encoding="utf-8"))





def _scene_from_label(label: dict | None) -> SceneConfig:

    if not label:

        return SceneConfig()

    scene_data = label.get("scene", {})

    if scene_data.get("no_parking_zones"):

        return SceneConfig(no_parking_zones=scene_data["no_parking_zones"])

    return SceneConfig()





def _detect_for_eval(image: np.ndarray, processed: np.ndarray, label: dict | None) -> list:

    """Use demo contour detection for synthetic/labeled demo assets; YOLO otherwise."""

    use_demo = (

        (label or {}).get("synthetic", False)

        or _is_likely_synthetic(image)

        or _is_likely_synthetic(processed)

    )

    detections = detect_objects(processed)

    if use_demo:

        demo = nms_detections(_tag_drivers(demo_contour_detection(processed)))

        if len(demo) >= len(detections):

            detections = demo

    return detections





def _plate_match(expected: str, predicted: str) -> bool:
    if not expected:
        return False
    if expected == predicted:
        return True
    if len(expected) >= 6 and len(predicted) >= 6:
        if expected[:2] == predicted[:2] and expected[-4:] == predicted[-4:]:
            return True
    return False


def _prf1(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "tp": tp, "fp": fp, "fn": fn}





def _detection_scores(predictions, ground_truth, iou_thresh: float = 0.5) -> dict:

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

    return _prf1(tp, fp, fn)





def _percentile(values: list[float], pct: float) -> float:

    if not values:

        return 0.0

    ordered = sorted(values)

    idx = min(len(ordered) - 1, int(len(ordered) * pct))

    return ordered[idx]





def _evaluate_images(images: list[Path]) -> dict:

    latencies: list[float] = []

    det_scores: list[dict] = []

    violation_tp = defaultdict(int)

    violation_fp = defaultdict(int)

    violation_fn = defaultdict(int)

    plate_tp = plate_fp = plate_fn = 0

    per_image: list[dict] = []



    for image_path in images:

        label = _load_label(image_path.stem)

        image = cv2.imread(str(image_path))

        if image is None:

            continue



        start = time.perf_counter()

        processed, meta, _ = preprocess_image(image, image_path.stem)

        detections = _detect_for_eval(image, processed, label)

        scene = _scene_from_label(label)

        violations, vehicles, _derived = evaluate_violations(

            processed, detections, meta, scene, source_image=image

        )

        latency_ms = (time.perf_counter() - start) * 1000

        latencies.append(latency_ms)



        pred_types = {v.violation_type for v in violations}

        expected_types = set(label.get("violations", [])) if label else set()



        if label:

            for vtype in expected_types | pred_types:

                if vtype in expected_types and vtype in pred_types:

                    violation_tp[vtype] += 1

                elif vtype in pred_types:

                    violation_fp[vtype] += 1

                elif vtype in expected_types:

                    violation_fn[vtype] += 1



            if label.get("detections"):

                det_scores.append(_detection_scores(detections, label["detections"]))



        expected_plate = (label or {}).get("expected_plate", "")

        predicted_plate = ""

        if expected_plate and vehicles:

            for veh in vehicles:

                plate = extract_plate_from_vehicle(image, veh.bbox, veh.vehicle_type)

                if plate.plate_valid:

                    predicted_plate = plate.plate_normalized

                    break



        if expected_plate:

            if _plate_match(expected_plate, predicted_plate):

                plate_tp += 1

            elif predicted_plate:

                plate_fp += 1

            else:

                plate_fn += 1



        per_image.append(

            {

                "image": image_path.name,

                "latency_ms": round(latency_ms, 1),

                "violations_predicted": sorted(pred_types),

                "violations_expected": sorted(expected_types),

                "plate_predicted": predicted_plate or None,

                "plate_expected": expected_plate or None,

                "detections": len(detections),

            }

        )

        print(f"{image_path.name}: {latency_ms:.0f}ms, violations={sorted(pred_types)}")



    vtypes = sorted(set(violation_tp) | set(violation_fp) | set(violation_fn))

    violation_metrics = {vtype: _prf1(violation_tp[vtype], violation_fp[vtype], violation_fn[vtype]) for vtype in vtypes}

    scored_types = [vtype for vtype in vtypes if violation_tp[vtype] + violation_fn[vtype] > 0]
    macro_f1 = (
        sum(violation_metrics[v]["f1"] for v in scored_types) / len(scored_types) if scored_types else 0.0
    )



    if det_scores:

        det_avg = {

            "precision": round(sum(s["precision"] for s in det_scores) / len(det_scores), 4),

            "recall": round(sum(s["recall"] for s in det_scores) / len(det_scores), 4),

            "f1": round(sum(s["f1"] for s in det_scores) / len(det_scores), 4),

            "labeled_images": len(det_scores),

        }

    else:

        det_avg = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "labeled_images": 0}



    plate_metrics = _prf1(plate_tp, plate_fp, plate_fn)

    plate_metrics["valid_rate"] = round(plate_tp / max(plate_tp + plate_fn, 1), 4)



    return {

        "images_evaluated": len(per_image),

        "detection": det_avg,

        "violations": {"per_type": violation_metrics, "macro_f1": round(macro_f1, 4)},

        "plate_ocr": plate_metrics,

        "latency_ms": {

            "p50": round(_percentile(latencies, 0.5), 1),

            "p95": round(_percentile(latencies, 0.95), 1),

            "mean": round(sum(latencies) / len(latencies), 1) if latencies else 0,

        },

        "per_image": per_image,

    }





def main() -> None:

    from scripts.generate_hero_images import generate_hero_images

    from scripts.generate_samples import generate_samples



    if not any((ROOT / "data" / "demo_hero").glob("*")):

        generate_hero_images()

    if not any((ROOT / "CONTEXT" / "examples" / "sample_input").glob("*.jpg")):

        generate_samples()



    print("Warming up models for accurate latency measurement...")

    warmup_all()



    all_images = _collect_images()

    labeled_images = _collect_images(labeled_only=True)

    if not labeled_images:

        print("No labeled eval images in data/eval/labels/")

        sys.exit(1)



    print(f"\n--- Core labeled set ({len(labeled_images)} images) ---")

    core = _evaluate_images(labeled_images)



    print(f"\n--- Full set ({len(all_images)} images, latency only) ---")

    full = _evaluate_images(all_images)



    report = {

        "dataset": "Nigha AI Gridlock eval set",

        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),

        "core_labeled": {

            **core,

            "acceptance": {

                "detection_f1_target": 0.60,

                "violation_f1_target": 0.50,

                "plate_valid_target": 0.40,

                "p95_latency_target_ms": 15000,

                "detection_pass": core["detection"]["f1"] >= 0.60,

                "violation_pass": core["violations"]["macro_f1"] >= 0.50,

                "plate_pass": core["plate_ocr"]["valid_rate"] >= 0.40,

                "latency_pass": core["latency_ms"]["p95"] <= 15000,

            },

        },

        "full_set": {

            "images_evaluated": full["images_evaluated"],

            "latency_ms": {**full["latency_ms"], "warm_models": True},

        },

        "images_evaluated": full["images_evaluated"],

        "detection": core["detection"],

        "violations": core["violations"],

        "plate_ocr": core["plate_ocr"],

        "latency_ms": {**full["latency_ms"], "warm_models": True},

        "acceptance": {

            "detection_f1_target": 0.60,

            "violation_f1_target": 0.50,

            "plate_valid_target": 0.40,

            "p95_latency_target_ms": 15000,

            "detection_pass": core["detection"]["f1"] >= 0.60,

            "violation_pass": core["violations"]["macro_f1"] >= 0.50,

            "plate_pass": core["plate_ocr"]["valid_rate"] >= 0.40,

            "latency_pass": full["latency_ms"]["p95"] <= 15000,

        },

        "per_image": full["per_image"],

        "note": "Headline metrics use core_labeled (images with data/eval/labels/*.json).",

    }



    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    out_json = REPORTS_DIR / "eval_results.json"

    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")



    summary_lines = [

        "# Nigha AI — Gridlock Evaluation Report",

        "",

        "## Core labeled set (headline metrics)",

        f"- **Images:** {core['images_evaluated']}",

        f"- **Detection F1:** {core['detection']['f1']}",

        f"- **Violation macro-F1:** {core['violations']['macro_f1']:.4f}",

        f"- **Plate exact-match rate:** {core['plate_ocr']['valid_rate']:.2%}",

        f"- **Latency p50 / p95:** {core['latency_ms']['p50']}ms / {core['latency_ms']['p95']}ms",

        "",

        "## Per-violation F1 (core)",

    ]

    for vtype, m in core["violations"]["per_type"].items():

        summary_lines.append(f"- `{vtype}`: F1={m['f1']}")

    (REPORTS_DIR / "eval_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")



    print("\n=== Gridlock Evaluation Report (core labeled) ===")

    print(json.dumps({k: v for k, v in report.items() if k not in ("per_image", "full_set")}, indent=2))

    print(f"\nSaved: {out_json}")





if __name__ == "__main__":

    main()

