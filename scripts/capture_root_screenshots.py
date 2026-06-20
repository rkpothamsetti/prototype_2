"""Regenerate root-level marketing/demo screenshots from the live dashboard."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT
BASE_URL = "http://localhost:5173"
API_URL = "http://127.0.0.1:8001"

VIOLATION_LABELS = {
    "helmet_non_compliance": "No Helmet",
    "triple_riding": "Triple Riding",
    "wrong_side_driving": "Wrong Side",
    "illegal_parking": "Illegal Parking",
}


def wait_url(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}")


def fetch_evidence() -> list[dict]:
    with urllib.request.urlopen(f"{API_URL}/api/v1/evidence?limit=200") as resp:
        return json.load(resp)


def pick_evidence(items: list[dict]) -> dict[str, str | None]:
    confirmed_plate = next(
        (e for e in items if e.get("review_status") == "confirmed" and e.get("plate_normalized")),
        None,
    )
    triple = next((e for e in items if "triple_riding" in (e.get("violation_type") or "")), None)
    pending = next(
        (e for e in items if e.get("review_status") == "pending_review" and e.get("violation_type") != "none"),
        None,
    )
    challan = confirmed_plate or next(
        (e for e in items if e.get("review_status") == "confirmed" and e.get("violation_type") != "none"),
        None,
    )
    return {
        "confirmed_plate_id": confirmed_plate["evidence_id"] if confirmed_plate else None,
        "triple_id": triple["evidence_id"] if triple else None,
        "pending_id": pending["evidence_id"] if pending else None,
        "challan_id": challan["evidence_id"] if challan else None,
    }


def main() -> None:
    from playwright.sync_api import sync_playwright

    wait_url(BASE_URL)
    wait_url(f"{API_URL}/health")
    picks = pick_evidence(fetch_evidence())

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        def click_nav(label: str) -> None:
            nav = page.locator("aside nav button, aside .nav-item").filter(has_text=label)
            if nav.count() == 0:
                nav = page.get_by_role("button", name=label)
            nav.first.click()
            page.wait_for_timeout(1000)

        def screenshot(name: str, full_page: bool = False) -> Path:
            path = OUT / name
            page.screenshot(path=str(path), full_page=full_page)
            print(f"Saved {path.name} ({path.stat().st_size} bytes)")
            return path

        def select_evidence_row(*text_hints: str) -> None:
            for hint in text_hints:
                row = page.locator("button").filter(has_text=hint)
                if row.count() > 0:
                    row.first.click()
                    page.wait_for_timeout(1200)
                    return
            raise RuntimeError(f"Could not find evidence row for hints: {text_hints}")

        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(2500)

        click_nav("Dashboard")
        screenshot("01-dashboard-overview.png")
        screenshot("09-dashboard-full-page.png", full_page=True)

        click_nav("Mobility")
        screenshot("02-mobility-intelligence.png")

        click_nav("Upload")
        screenshot("03-upload-media.png")

        click_nav("Evidence")
        page.wait_for_timeout(1000)
        screenshot("04-evidence-review-queue.png")
        screenshot("evidence-tab-screenshot.png")

        if picks["pending_id"]:
            pending = next(e for e in fetch_evidence() if e["evidence_id"] == picks["pending_id"])
            label = VIOLATION_LABELS.get(pending.get("violation_type", "").split(",")[0].strip(), "No Helmet")
            select_evidence_row(label)

        if picks["confirmed_plate_id"]:
            confirmed = next(e for e in fetch_evidence() if e["evidence_id"] == picks["confirmed_plate_id"])
            select_evidence_row(confirmed.get("plate_normalized") or "No Helmet")
            screenshot("06-evidence-confirmed-plate.png")

        if picks["triple_id"]:
            select_evidence_row("Triple Riding")
            screenshot("08-triple-riding-evidence.png")

        if picks["challan_id"]:
            challan_ev = next(e for e in fetch_evidence() if e["evidence_id"] == picks["challan_id"])
            select_evidence_row(
                challan_ev.get("plate_normalized") or "No Helmet",
                "Triple Riding",
            )
            issue_btn = page.get_by_role("button", name="View / Download e-Challan")
            confirm_btn = page.get_by_role("button", name="Confirm & Issue e-Challan")
            if confirm_btn.count() > 0 and confirm_btn.first.is_enabled():
                confirm_btn.first.click()
                page.wait_for_timeout(3500)
            elif issue_btn.count() > 0 and issue_btn.first.is_enabled():
                issue_btn.first.click()
                page.wait_for_timeout(2500)
            screenshot("07-e-challan-receipt.png")
            screenshot("challan-receipt-screenshot.png")

        browser.close()


if __name__ == "__main__":
    main()
