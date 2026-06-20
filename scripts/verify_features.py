"""End-to-end feature verification script."""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8001"
SAMPLES = Path(__file__).resolve().parent.parent / "CONTEXT" / "examples" / "sample_input"


def main() -> None:
    results: dict[str, str] = {}
    client = httpx.Client(timeout=180.0)

    try:
        h = client.get(f"{BASE}/health").json()
        results["health"] = "OK" if h.get("app") == "Nigha AI" else "FAIL"
    except Exception as exc:
        results["health"] = f"FAIL: {exc}"
        print(json.dumps(results, indent=2))
        return

    samples = {
        "motorcycle_rider.jpg": "helmet_non_compliance",
        "triple_riding.jpg": "triple_riding",
        "illegal_parking.jpg": "illegal_parking",
        "car_with_plate.jpg": None,
    }

    for filename, expected in samples.items():
        path = SAMPLES / filename
        if not path.exists():
            results[filename] = "SKIP: file missing"
            continue
        with path.open("rb") as f:
            r = client.post(
                f"{BASE}/api/v1/media/upload",
                files={"file": (filename, f, "image/jpeg")},
                data={
                    "latitude": "12.9750",
                    "longitude": "77.6063",
                    "camera_id": "CAM_BLR_MG_01",
                    "camera_id": "CAM_TEST",
                    "no_parking_zones": "[[100,300,500,600]]",
                },
            )
        if r.status_code != 200:
            results[filename] = f"FAIL upload {r.status_code}"
            continue
        job_id = r.json()["job_id"]
        status = "timeout"
        for _ in range(40):
            j = client.get(f"{BASE}/api/v1/jobs/{job_id}").json()
            if j["status"] == "completed":
                types = [e["violation"]["type"] for e in j.get("evidence", [])]
                types = [t for t in types if t != "none"]
                if expected and expected in types:
                    results[filename] = f"OK ({expected})"
                elif expected:
                    results[filename] = f"PARTIAL: got {types}, expected {expected}"
                elif filename == "car_with_plate.jpg":
                    plates = []
                    for e in j.get("evidence", []):
                        p = e.get("vehicle", {}).get("plate")
                        if p:
                            plates.append(p)
                    # also check DB fields via job evidence
                    results[filename] = "OK" if any("AP09AB" in (p or "") for p in plates) else f"PARTIAL: plates={plates}"
                else:
                    results[filename] = f"OK: {types}"
                status = "done"
                break
            if j["status"] == "failed":
                results[filename] = f"FAIL: {j.get('error_message')}"
                status = "done"
                break
            time.sleep(2)
        if status == "timeout":
            results[filename] = "FAIL: timeout"

    ev = client.get(f"{BASE}/api/v1/evidence").json()
    results["evidence_search"] = "OK" if isinstance(ev, list) else "FAIL"

    a = client.get(f"{BASE}/api/v1/analytics/summary").json()
    results["analytics"] = "OK" if "total_violations" in a else "FAIL"

    m = client.get(f"{BASE}/api/v1/metrics").json()
    results["metrics"] = "OK" if "latency_p95_ms" in m else "FAIL"

    if ev:
        eid = ev[0]["evidence_id"]
        rev = client.patch(f"{BASE}/api/v1/evidence/{eid}/review?review_status=confirmed").json()
        results["review"] = "OK" if rev.get("review_status") == "confirmed" else "FAIL"

    print("\n=== Nigha AI Feature Check ===")
    for k, v in results.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
