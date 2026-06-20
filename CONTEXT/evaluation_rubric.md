# TrafficVision AI — Evaluation Rubric

## Detection Metrics (mAP)

- Compute mAP@0.5 for vehicle classes (car, motorcycle, bus, truck, person).
- Ground truth: `CONTEXT/examples/expected_output/*.json` detection bboxes.

## Violation Classification Metrics

Per violation type:

- **Precision** = TP / (TP + FP)
- **Recall** = TP / (TP + FN)
- **F1** = 2 * P * R / (P + R)
- **Accuracy** = correct predictions / total labeled samples

## System Metrics

- **Latency**: p50 and p95 end-to-end processing time per image (ms).
- **Throughput**: images processed per second in batch mode.

## Acceptance Thresholds (MVP demo)

| Metric | Target |
|--------|--------|
| Vehicle detection mAP@0.5 | ≥ 0.60 on eval set |
| Violation F1 (helmet, triple, parking) | ≥ 0.50 on eval set |
| Plate OCR valid rate | ≥ 0.40 on visible plates |
| p95 latency (CPU, 1280px) | ≤ 15000 ms |

Run: `python scripts/evaluate.py`
