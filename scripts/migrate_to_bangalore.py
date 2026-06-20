"""Migrate legacy Hyderabad coordinates and camera IDs to Bangalore."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from config import DATA_DIR, DB_PATH
from db.database import engine

# Bangalore CCTV zones (lat, lng, camera_id)
BLR_ZONES = [
    (12.9750, 77.6063, "CAM_BLR_MG_01"),
    (12.9176, 77.6234, "CAM_BLR_SILK_01"),
    (13.0358, 77.5970, "CAM_BLR_HEBBAL_01"),
    (12.8399, 77.6770, "CAM_BLR_ECITY_01"),
    (12.9784, 77.6408, "CAM_BLR_INDIRA_01"),
]

HYD_LAT, HYD_LNG = 17.385, 78.4867
TOLERANCE = 0.5


def is_hyderabad(lat: float | None, lng: float | None) -> bool:
    if lat is None or lng is None:
        return False
    return abs(lat - HYD_LAT) < TOLERANCE and abs(lng - HYD_LNG) < TOLERANCE


def migrate_db() -> int:
    if not DB_PATH.exists():
        print(f"No database at {DB_PATH}")
        return 0

    updated = 0
    with engine.connect() as conn:
        for table in ("evidence", "media"):
            try:
                rows = conn.execute(
                    text(f"SELECT rowid, latitude, longitude, camera_id FROM {table}")
                ).fetchall()
            except Exception:
                continue

            for i, row in enumerate(rows):
                rid, lat, lng, cam = row[0], row[1], row[2], row[3]
                needs_cam = cam and ("HYD" in str(cam).upper() or cam == "CAM_HYD_01")
                needs_geo = is_hyderabad(lat, lng)
                if not needs_cam and not needs_geo:
                    continue

                zone = BLR_ZONES[i % len(BLR_ZONES)]
                new_lat, new_lng, new_cam = zone[0], zone[1], zone[2]
                jitter = (i % 3) * 0.002
                conn.execute(
                    text(
                        f"UPDATE {table} SET latitude = :lat, longitude = :lng, camera_id = :cam WHERE rowid = :rid"
                    ),
                    {"lat": new_lat + jitter, "lng": new_lng + jitter, "cam": new_cam, "rid": rid},
                )
                updated += 1

        conn.commit()
    return updated


def migrate_json_evidence() -> int:
    evidence_dir = DATA_DIR / "evidence"
    if not evidence_dir.exists():
        return 0

    count = 0
    for path in evidence_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        changed = False
        loc = data.get("location") or data
        lat = loc.get("lat") if isinstance(loc, dict) else None
        lng = loc.get("lng") if isinstance(loc, dict) else None

        if is_hyderabad(lat, lng):
            zone = BLR_ZONES[count % len(BLR_ZONES)]
            if "location" in data and isinstance(data["location"], dict):
                data["location"]["lat"] = zone[0]
                data["location"]["lng"] = zone[1]
                if "camera_id" in data["location"] or data["location"].get("camera_id"):
                    data["location"]["camera_id"] = zone[2]
            else:
                data["lat"] = zone[0]
                data["lng"] = zone[1]
            changed = True

        cam = None
        if isinstance(data.get("location"), dict):
            cam = data["location"].get("camera_id")
        cam = cam or data.get("camera_id")
        if cam and "HYD" in str(cam).upper():
            zone = BLR_ZONES[count % len(BLR_ZONES)]
            if isinstance(data.get("location"), dict):
                data["location"]["camera_id"] = zone[2]
            data["camera_id"] = zone[2]
            changed = True

        if changed:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            count += 1

    return count


if __name__ == "__main__":
    db_n = migrate_db()
    json_n = migrate_json_evidence()
    print(f"Migrated {db_n} DB rows and {json_n} JSON evidence files to Bangalore.")
