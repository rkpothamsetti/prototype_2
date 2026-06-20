"""Test helpers."""
from __future__ import annotations

from services.association.engine import AssociatedPerson, VehicleRecord


def make_vehicle_record(
    vehicle_id: str = "VEH-001",
    vehicle_type: str = "motorcycle",
    bbox: list[float] | None = None,
    riders: int = 1,
) -> VehicleRecord:
    bbox = bbox or [100, 150, 400, 450]
    persons = []
    for i in range(riders):
        persons.append(
            AssociatedPerson(
                person_id=f"r{i}",
                bbox=[120 + i * 60, 60, 180 + i * 60, 200],
                confidence=0.85,
                role="rider",
                helmet_detected=False,
                proximity_score=0.8,
            )
        )
    return VehicleRecord(
        vehicle_id=vehicle_id,
        vehicle_type=vehicle_type,
        track_id="track-1",
        bbox=bbox,
        confidence=0.9,
        associated_persons=persons,
        rider_count=riders,
    )
