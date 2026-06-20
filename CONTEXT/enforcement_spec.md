# Traffic Enforcement Vision — Agent Specification

This document is the authoritative behavior contract for TrafficVision AI agents.

## Detection Classes (instance-level)

| Class | Source |
|-------|--------|
| motorcycle, car, bus, truck, bicycle | YOLO COCO |
| person | YOLO |
| helmet | Derived (head ROI + shell analysis) |
| seatbelt | Derived (driver torso ROI) |
| license_plate | Derived (white-region + OCR) |
| traffic_signal | Derived (HSV color blobs) |
| stop_line | Scene config + line detection |

## Pipeline Stages

1. **Detection** — YOLO instance detection + NMS de-duplication (`services/detection`, `services/association/engine.nms_detections`)
2. **Tracking** — Unique track IDs across video frames (`services/tracking`)
3. **Association** — Scene graph: vehicles `VEH-001+`, riders/drivers/passengers, helmets (`services/association/engine`)
4. **Violation reasoning** — Per-vehicle rules only (`services/violation_reasoning/vehicle_eval`)
5. **OCR** — License plate per vehicle bbox + full-image scan (`services/ocr`)
6. **Evidence** — Green/red annotated image + enforcement JSON (`services/evidence`)

## Rules

1. Every object gets an independent bounding box (NMS de-duplication).
2. Every vehicle gets a unique ID: `VEH-001`, `VEH-002`, …
3. Riders/passengers/drivers are associated to vehicles via IoU + proximity scoring.
4. Helmets are associated to the correct rider person ID.
5. Violations are **never** global — each violation links to exactly one `vehicle_id`.
6. Multiple violations may apply to the same vehicle.
7. Output per vehicle: ID, type, bbox, plate, persons, violations, confidence.
8. Annotated image: **Green** = compliant, **Red** = violation; show Vehicle ID + violation types.
9. Emit structured enforcement JSON for each job (`{media_id}_enforcement.json`).

## Enforcement JSON Schema

```json
{
  "media_id": "...",
  "job_id": "...",
  "timestamp": "ISO-8601",
  "vehicles": [
    {
      "vehicle_id": "VEH-001",
      "vehicle_type": "motorcycle",
      "bounding_box": [x1, y1, x2, y2],
      "license_plate": { "plate_normalized": "OD032943", "plate_valid": true },
      "associated_persons": [{ "person_id": "...", "role": "rider", "helmet_detected": true }],
      "rider_count": 1,
      "violations": [],
      "compliance_status": "compliant",
      "confidence": 0.87
    }
  ],
  "derived_objects": [],
  "annotated_path": "..."
}
```

## Violation Types (per vehicle)

- `helmet_non_compliance`
- `triple_riding`
- `seatbelt_non_compliance`
- `stop_line_violation`
- `red_light_violation`
- `wrong_side_driving`
- `illegal_parking`