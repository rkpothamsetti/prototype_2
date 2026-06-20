"""Printable e-Challan receipt HTML (government challan slip style)."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

from services.challan.branding import nigha_logo_data_uri

VIOLATION_LABELS = {
    "helmet_non_compliance": "Riding without protective headgear (Helmet)",
    "triple_riding": "Triple riding on two-wheeler",
    "wrong_side_driving": "Wrong-side driving",
    "illegal_parking": "Parking in no-parking zone",
    "seatbelt_non_compliance": "Driving without seatbelt",
    "stop_line_violation": "Stop line violation",
    "red_light_violation": "Signal jump / red light violation",
}

RECEIPT_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: #f3f4f6;
  color: #111827;
  padding: 24px;
}
.receipt {
  position: relative;
  max-width: 420px;
  margin: 0 auto;
  background: #fff;
  border: 1px solid #d1d5db;
  box-shadow: 0 8px 24px rgba(0,0,0,.08);
  overflow: hidden;
}
.receipt::before {
  content: '';
  position: absolute;
  inset: 0;
  background-repeat: no-repeat;
  background-position: center 42%;
  background-size: 58% auto;
  opacity: 0.09;
  pointer-events: none;
  z-index: 0;
}
.receipt-header,
.body {
  position: relative;
  z-index: 1;
}
.receipt-header {
  background: linear-gradient(135deg, #1e3a5f 0%, #0f766e 100%);
  color: #fff;
  text-align: center;
  padding: 18px 16px 14px;
}
.receipt-header h1 { font-size: 13px; letter-spacing: .08em; font-weight: 700; }
.receipt-header h2 { font-size: 18px; margin-top: 6px; font-weight: 800; }
.receipt-header p { font-size: 11px; opacity: .9; margin-top: 4px; }
.draft-badge {
  display: inline-block;
  margin-top: 10px;
  padding: 3px 10px;
  border: 1px dashed rgba(255,255,255,.7);
  font-size: 10px;
  letter-spacing: .12em;
}
.body { padding: 16px 18px 20px; }
.row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 7px 0;
  font-size: 12px;
  border-bottom: 1px dotted #e5e7eb;
}
.row:last-child { border-bottom: none; }
.label { color: #6b7280; flex-shrink: 0; }
.value { font-weight: 600; text-align: right; word-break: break-word; }
.section-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .1em;
  color: #0f766e;
  margin: 14px 0 6px;
  text-transform: uppercase;
}
.amount-box {
  margin: 16px 0;
  border: 2px solid #111827;
  padding: 12px;
  text-align: center;
}
.amount-box .amt-label { font-size: 11px; color: #6b7280; }
.amount-box .amt-value {
  font-size: 28px;
  font-weight: 800;
  font-family: 'Courier New', monospace;
  margin-top: 4px;
}
.barcode {
  margin: 14px 0 8px;
  height: 42px;
  background: repeating-linear-gradient(
    90deg,
    #111 0 2px,
    #fff 2px 4px,
    #111 4px 5px,
    #fff 5px 8px
  );
}
.footer {
  font-size: 10px;
  color: #6b7280;
  line-height: 1.5;
  border-top: 2px dashed #d1d5db;
  padding-top: 12px;
  margin-top: 8px;
}
.print-hint {
  text-align: center;
  font-size: 11px;
  color: #9ca3af;
  margin-top: 16px;
}
@media print {
  body { background: #fff; padding: 0; }
  .receipt { box-shadow: none; border: none; max-width: 100%; }
  .print-hint { display: none; }
}
"""


def render_receipt_html(challan: dict[str, Any]) -> str:
    """Build a self-contained printable e-Challan receipt page."""
    logo_uri = nigha_logo_data_uri()
    logo_bg_css = (
        f"background-image: url('{logo_uri}');" if logo_uri else "background-image: none;"
    )
    receipt_css = RECEIPT_CSS.replace(
        "background-repeat: no-repeat;",
        f"{logo_bg_css} background-repeat: no-repeat;",
        1,
    )
    reg = html.escape(str(challan.get("registration_number") or "UNKNOWN"))
    challan_no = html.escape(str(challan.get("challan_number") or "—"))
    violation_label = html.escape(
        str(challan.get("violation_label") or challan.get("violation_code") or "Traffic violation")
    )
    section = html.escape(str(challan.get("violation_section") or "177"))
    amount = int(challan.get("fine_amount_inr") or 0)
    generated = challan.get("generated_at") or datetime.now(timezone.utc).isoformat()
    try:
        dt = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        date_str = dt.astimezone(timezone.utc).strftime("%d %b %Y")
        time_str = dt.astimezone(timezone.utc).strftime("%H:%M IST")
    except ValueError:
        date_str = generated[:10]
        time_str = "—"

    due = challan.get("payment_due_date") or ""
    due_esc = html.escape(str(due))
    camera = html.escape(str((challan.get("location") or {}).get("camera_id") or "—"))
    lat = (challan.get("location") or {}).get("lat")
    lng = (challan.get("location") or {}).get("lng")
    loc = html.escape(f"{lat:.5f}, {lng:.5f}" if lat is not None and lng is not None else "—")
    officer = html.escape(str(challan.get("officer_id") or "—"))
    vehicle_id = html.escape(str(challan.get("vehicle_id") or "—"))
    vehicle_class = html.escape(str(challan.get("vehicle_class") or "—"))
    evidence_id = html.escape(str(challan.get("evidence_id") or "—"))
    confidence = challan.get("confidence")
    conf_str = html.escape(f"{float(confidence) * 100:.1f}%") if confidence is not None else "—"
    dispute = html.escape(str(challan.get("dispute_url") or ""))
    channels = challan.get("payment_channels") or []
    channels_str = html.escape(", ".join(channels))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>e-Challan {challan_no}</title>
  <style>{receipt_css}</style>
</head>
<body>
  <div class="receipt">
    <div class="receipt-header">
      <h1>GOVERNMENT OF INDIA · MINISTRY OF ROAD TRANSPORT</h1>
      <h2>E-CHALLAN RECEIPT</h2>
      <p>Integrated Traffic Enforcement · Nigha AI</p>
      <span class="draft-badge">OFFICER CONFIRMED DRAFT</span>
    </div>
    <div class="body">
      <div class="row"><span class="label">Challan No.</span><span class="value">{challan_no}</span></div>
      <div class="row"><span class="label">Date</span><span class="value">{date_str}</span></div>
      <div class="row"><span class="label">Time (UTC)</span><span class="value">{time_str}</span></div>
      <div class="row"><span class="label">Payment due</span><span class="value">{due_esc}</span></div>

      <p class="section-title">Vehicle</p>
      <div class="row"><span class="label">Registration</span><span class="value">{reg}</span></div>
      <div class="row"><span class="label">Vehicle ID</span><span class="value">{vehicle_id}</span></div>
      <div class="row"><span class="label">Class</span><span class="value">{vehicle_class}</span></div>

      <p class="section-title">Violation</p>
      <div class="row"><span class="label">Offence</span><span class="value">{violation_label}</span></div>
      <div class="row"><span class="label">MV Act Sec.</span><span class="value">{section}</span></div>
      <div class="row"><span class="label">AI confidence</span><span class="value">{conf_str}</span></div>

      <p class="section-title">Location</p>
      <div class="row"><span class="label">Camera</span><span class="value">{camera}</span></div>
      <div class="row"><span class="label">Coordinates</span><span class="value">{loc}</span></div>

      <div class="amount-box">
        <div class="amt-label">PENALTY FOR THIS OFFENCE</div>
        <div class="amt-value">₹ {amount:,}</div>
        <div class="amt-label" style="margin-top:6px;font-size:10px">Sec. {section} · {violation_label}</div>
      </div>

      <div class="barcode" aria-hidden="true"></div>
      <div class="row"><span class="label">Evidence ref</span><span class="value">{evidence_id}</span></div>
      <div class="row"><span class="label">Issuing officer</span><span class="value">{officer}</span></div>

      <div class="footer">
        <p><strong>Payment:</strong> {channels_str}</p>
        <p><strong>Dispute / pay online:</strong> {dispute}</p>
        <p style="margin-top:8px">This is a system-generated e-Challan draft for officer review.
        Not valid for prosecution until synced with the official Parivahan e-Challan portal.</p>
      </div>
    </div>
  </div>
  <p class="print-hint">Use Print (Ctrl+P) to save as PDF or print this receipt.</p>
  <script>window.onload = function() {{ /* optional auto-print: window.print(); */ }};</script>
</body>
</html>"""
