# Nigha AI

**Per-vehicle traffic enforcement for Indian cities.** Upload CCTV or traffic media, detect violations per vehicle (`VEH-001`, …), OCR Indian plates, and route explainable evidence to an officer review queue — AI proposes, humans decide.

> **Nigha AI — Scale enforcement without losing accountability.**

---

## Table of contents

1. [What this project does](#what-this-project-does)
2. [Quick start (5 minutes)](#quick-start-5-minutes)
3. [Full local setup](#full-local-setup)
4. [Verify everything works](#verify-everything-works)
5. [Officer demo walkthrough](#officer-demo-walkthrough)
6. [Project structure](#project-structure)
7. [Architecture & pipeline](#architecture--pipeline)
8. [Violation detection modules](#violation-detection-modules)
9. [Configuration reference](#configuration-reference)
10. [API reference](#api-reference)
11. [Running tests](#running-tests)
12. [Deployment](#deployment)
13. [Troubleshooting](#troubleshooting)
14. [Related documents](#related-documents)

---

## What this project does

Indian cities generate huge volumes of traffic footage, but police cannot manually review all of it. Naive “AI challan” tools fail because they label whole images instead of answering:

1. **Which vehicle** broke the rule?
2. **What rule** was broken, and **why**?
3. **Can an officer defend** this in a dispute?

Nigha AI processes each vehicle separately, attaches explainable evidence (plate, violation type, confidence, bounding boxes), and routes cases to an officer review queue before any challan is issued.

**Supported violations:** helmet non-compliance, triple riding, wrong-side driving, illegal parking, seatbelt non-compliance, stop-line violation, red-light violation.

---

## Quick start (5 minutes)

**Prerequisites:** Python 3.10+ (3.11 recommended), Node.js 18+, ~2 GB RAM.

### Windows

```powershell
git clone https://github.com/rkpothamsetti/prototype_2.git
cd prototype_2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Terminal 1 — API**

```powershell
python run_server.py
```

Wait until http://localhost:8001/health shows `"models_ready": true` (first run downloads YOLO weights — 1–3 minutes).

**Terminal 2 — Dashboard**

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

**Or use the shortcut:** double-click `start.bat` from the project root (opens both servers in separate windows).

### macOS / Linux

```bash
git clone https://github.com/rkpothamsetti/prototype_2.git
cd prototype_2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_server.py          # terminal 1
cd frontend && npm install && npm run dev   # terminal 2
```

---

## Full local setup

### Step 1 — Clone the repository

```bash
git clone https://github.com/rkpothamsetti/prototype_2.git
cd prototype_2
```

The repo folder may be named `prototype_2` or whatever you cloned it as locally.

### Step 2 — Python virtual environment

```bash
python -m venv .venv
```

| Platform | Activate |
|----------|----------|
| Windows PowerShell | `.\.venv\Scripts\Activate.ps1` |
| Windows CMD | `.venv\Scripts\activate.bat` |
| macOS / Linux | `source .venv/bin/activate` |

Install dependencies:

```bash
pip install -r requirements.txt
```

**What gets installed:** FastAPI, Ultralytics YOLO, OpenCV, EasyOCR, MediaPipe (rider pose), SQLAlchemy, pytest, and supporting libraries.

### Step 3 — Optional: helmet YOLO model (recommended for local dev)

Helmet detection works without this (heuristic fallback), but accuracy improves with dedicated weights.

```powershell
# PowerShell — from project root
mkdir -Force data\models
curl -fsSL -o data\models\helmet_yolo.pt `
  "https://huggingface.co/iam-tsr/yolov8n-helmet-detection/resolve/main/best.pt"
```

```bash
# macOS / Linux
mkdir -p data/models
curl -fsSL -o data/models/helmet_yolo.pt \
  "https://huggingface.co/iam-tsr/yolov8n-helmet-detection/resolve/main/best.pt"
```

Ensure `TV_USE_HELMET_YOLO=true` (this is the default locally). The Docker/Render build downloads this automatically.

### Step 4 — Data directories (auto-created)

On first run, the app creates:

```
data/
├── trafficvision.db      # SQLite database
├── uploads/              # Uploaded media
├── processed/            # Preprocessed frames
├── evidence/             # Annotated images + enforcement JSON
├── feedback/             # Officer rejection feedback
└── models/               # Optional helmet YOLO weights
```

These paths are gitignored — nothing in `data/` is committed.

### Step 5 — Start the backend

```bash
python run_server.py
```

| URL | Purpose |
|-----|---------|
| http://localhost:8001 | API root |
| http://localhost:8001/docs | Swagger interactive docs |
| http://localhost:8001/health | Health + `models_ready` flag |

**First startup:** YOLO (`yolo11n.pt`) and EasyOCR load automatically. With `TV_WARMUP_BLOCKING=true` (default locally), the server blocks until models are ready.

**Windows helper:** `start_server.ps1` kills any process on port 8001, creates the venv if missing, and starts the API.

### Step 6 — Start the frontend

In a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

| URL | Purpose |
|-----|---------|
| http://localhost:5173 | Officer dashboard |

Vite proxies `/api` and `/health` to port **8001** — both processes must stay running.

**Production build:**

```bash
cd frontend
npm run build    # output → frontend/dist/
```

Set `VITE_API_URL` to your hosted API origin when building for Vercel/Render.

---

## Verify everything works

### 1. Health check

```bash
curl http://localhost:8001/health
```

Expected (after warmup):

```json
{
  "status": "ok",
  "models_ready": true,
  "app": "Nigha AI"
}
```

### 2. Run the test suite

```bash
# From project root, venv activated
python -m pytest
```

**70 tests** cover pipeline, violations, OCR, API, evidence review, challan export, and security. Tests use synthetic images — no real media required.

### 3. Upload a sample

1. Open http://localhost:5173
2. Confirm sidebar shows **Backend connected** and models ready
3. Go to **Upload** → select a traffic image (JPEG/PNG) or short MP4
4. Click **Analyze** → wait for redirect to **Evidence**

---

## Officer demo walkthrough

### Step 1 — Open the dashboard

Go to **http://localhost:5173**. Sidebar should show backend connected and models ready.

### Step 2 — Upload traffic media

1. Open the **Upload** tab
2. Choose a traffic image or short video (JPEG/PNG/MP4, max 150 MB)
3. Location defaults to **Bengaluru** (`CAM_BLR_MG_01`, MG Road Junction)
4. Optionally expand **Advanced scene rules**:
   - `legal_direction_angle` — expected traffic flow in degrees (wrong-side detection)
   - `no_parking_zones` — pixel rectangles `[[x1,y1,x2,y2], ...]`
   - `stop_line_y` + `signal_state` — stop-line violations
   - `intersection_roi` + `traffic_light_state` — red-light violations
5. Click **Analyze**

### Step 3 — Processing stages

| Stage | What happens |
|-------|----------------|
| Ingestion | File saved with camera metadata |
| Preprocessing | Quality check, CLAHE normalization |
| Detection | YOLO — vehicles, persons |
| Tracking | IoU tracker across video frames (video only) |
| Association | Scene graph — riders/drivers linked to `VEH-001`, … |
| Violation reasoning | Per-vehicle rules with confidence + reason |
| OCR | Indian plate validation (e.g. `KA01AB1234`) |
| Evidence | Annotated image + `{media_id}_enforcement.json` |

### Step 4 — Review evidence

1. **Evidence** tab — filter by plate, violation type, or review status
2. Select a case — annotated image appears (green = compliant, red = violation)
3. **Confirm** (`C`) or **Reject** (`R`) via buttons or keyboard
4. Confirmed cases can export a challan receipt

### Step 5 — Analytics

- **Dashboard** — KPIs, violation trends, Bengaluru hotspot map, review queue
- **Mobility** — congestion classification and traffic-flow analytics

---

## Project structure

```
prototype_2/                          # repo root (Nigha AI)
│
├── api/
│   └── main.py                       # FastAPI routes, WebSocket jobs, CORS, auth
│
├── db/
│   ├── database.py                   # SQLAlchemy engine & session
│   └── models.py                     # Media, Evidence, ProcessingJob, AuditLog
│
├── services/                         # All backend business logic
│   ├── pipeline.py                   # End-to-end orchestrator (image + video)
│   ├── warmup.py                     # Preload YOLO, OCR, helmet model on startup
│   │
│   ├── ingestion/                    # Upload intake & RTSP frame capture
│   │   ├── service.py
│   │   └── rtsp.py
│   │
│   ├── preprocessing/                # CLAHE, blur gate, quality score
│   │   └── service.py
│   │
│   ├── detection/                    # Object detection
│   │   ├── service.py                # Main YOLO (vehicles, persons)
│   │   ├── helmet_yolo.py            # Dedicated helmet / no-helmet YOLO
│   │   └── demo_fallback.py          # OpenCV fallback for synthetic demo images
│   │
│   ├── tracking/                     # IoU multi-frame tracker (video)
│   │   └── service.py
│   │
│   ├── association/                  # Scene graph — link people to vehicles
│   │   ├── engine.py                 # Vehicle IDs, rider/driver roles, derived objects
│   │   └── pose_rider.py             # Seated-rider detection, triple-riding logic
│   │
│   ├── violation_reasoning/          # Per-vehicle violation rules
│   │   ├── service.py                # Entry: evaluate_violations()
│   │   ├── vehicle_eval.py           # All violation rules (helmet, triple, wrong-side, …)
│   │   ├── helmet.py                 # Heuristic helmet scoring on head ROI
│   │   ├── helmet_eval.py            # Hybrid YOLO + heuristic helmet assessment
│   │   └── temporal.py               # Video: aggregate violations across frames
│   │
│   ├── ocr/                          # Indian license plate OCR
│   │   └── service.py                # EasyOCR, format validation, fragment assembly
│   │
│   ├── evidence/                     # Annotated output
│   │   ├── service.py                # Enforcement JSON + image annotation
│   │   └── video.py                  # Annotated demo video for uploads
│   │
│   ├── analytics/                    # Dashboard data
│   │   ├── service.py                # KPIs, evidence search, metrics
│   │   └── mobility.py               # Congestion & traffic-flow analytics
│   │
│   ├── congestion/                   # Congestion classifier
│   │   └── classifier.py
│   │
│   ├── challan/                      # Penalty amounts & receipt export
│   │   ├── export.py
│   │   ├── receipt.py
│   │   ├── penalties.py
│   │   └── branding.py
│   │
│   ├── review/                       # Confidence-tier routing
│   │   └── tiers.py
│   │
│   ├── feedback/                     # Officer rejection → active learning stats
│   │   └── service.py
│   │
│   ├── jobs/                         # Background job queue & WebSocket events
│   │   ├── queue.py
│   │   └── events.py
│   │
│   ├── security/                     # Optional JWT / API key auth
│   │   ├── auth.py
│   │   └── paths.py
│   │
│   └── common/
│       └── utils.py                  # Bbox helpers, IoU, plate normalization
│
├── frontend/                         # React officer dashboard (Vite + Tailwind)
│   ├── src/
│   │   ├── App.jsx                   # Main layout & routing
│   │   ├── api.js                    # API client (proxies locally, VITE_API_URL in prod)
│   │   ├── constants.js              # Violation labels, colors, penalties
│   │   ├── config/
│   │   │   ├── city.js               # Bengaluru cameras & map bounds
│   │   │   └── theme.js
│   │   ├── components/
│   │   │   ├── dashboard/            # DashboardView, Charts, HotspotMap, MobilityView, …
│   │   │   ├── evidence/             # EvidenceView — review queue
│   │   │   ├── upload/               # UploadView — media + scene rules
│   │   │   ├── challan/              # ChallanReceipt
│   │   │   ├── layout/               # Sidebar, TopBar, MobileNav
│   │   │   └── ui/                   # StatCard, StatusBadge, Skeleton, …
│   │   └── utils/format.js
│   ├── vite.config.js                # Dev server port 5173, API proxy → 8001
│   └── package.json
│
├── CONTEXT/                          # Specs & rule definitions (not runtime code)
│   ├── enforcement_spec.md           # Enforcement JSON contract
│   ├── violation_rules.yaml          # Thresholds & reason templates
│   ├── data_schema.sql
│   └── examples/edge_cases.md
│
├── tests/                            # 70 pytest tests
│   ├── conftest.py
│   ├── test_violations.py
│   ├── test_association.py
│   ├── test_helmet_yolo.py
│   ├── test_helmet_plate.py
│   ├── test_pipeline.py
│   ├── test_api.py
│   └── …
│
├── config.py                         # Settings (TV_* env prefix)
├── schemas.py                        # Pydantic request/response models
├── run_server.py                     # Uvicorn entry point
├── requirements.txt                  # Python dependencies
├── pytest.ini
│
├── start.bat                         # Windows: launch API + frontend
├── start_server.ps1                  # Windows: safe API start on port 8001
│
├── Dockerfile                        # Render / Docker API image
├── render.yaml                       # Render Blueprint (API + static frontend)
├── vercel.json                       # Vercel frontend config
│
├── data/                             # Created at runtime (gitignored)
├── SOLUTION.md                       # Full solution write-up & roadmap
└── DEPLOY_LIVE.md                    # Live demo URLs (local reference)
```

---

## Architecture & pipeline

```mermaid
flowchart TB
    subgraph UI["Officer Dashboard (React :5173)"]
        DASH[Dashboard & KPIs]
        UP[Upload Portal]
        EV[Evidence Review]
    end

    subgraph API["FastAPI Gateway :8001"]
        REST[REST + WebSocket jobs]
        QUEUE[Background job queue]
    end

    subgraph Pipeline["Enforcement Pipeline"]
        ING[Ingestion]
        PRE[Preprocessing]
        DET[YOLO Detection]
        TRK[Tracking]
        ASC[Scene Graph]
        VIO[Violation Reasoning]
        OCR[Indian Plate OCR]
        EVI[Evidence Generation]
    end

    subgraph Store["Persistence"]
        DB[(SQLite)]
        FILES[Annotated images + JSON]
    end

    UP --> REST --> ING
    ING --> PRE --> DET --> TRK --> ASC --> VIO --> OCR --> EVI
    EVI --> DB
    EVI --> FILES
    DB --> DASH
    DB --> EV
    REST --> QUEUE
```

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, Tailwind CSS, Recharts, Leaflet, Framer Motion |
| API | FastAPI, Uvicorn (port **8001**) |
| CV / ML | Ultralytics YOLOv11, optional helmet YOLO, OpenCV, EasyOCR, MediaPipe |
| Database | SQLite + SQLAlchemy (PostgreSQL via `TV_DATABASE_URL`) |
| Dev proxy | Vite (port **5173**) → `/api` and `/health` → backend |

### Pipeline stages

| Stage | Module | Output |
|-------|--------|--------|
| 1. Ingestion | `services/ingestion` | Media record with lat/lng, `camera_id`, timestamp |
| 2. Preprocessing | `services/preprocessing` | Quality score; reject blurry frames |
| 3. Detection | `services/detection` | Bboxes: vehicles, persons |
| 4. Tracking | `services/tracking` | Stable track IDs across video frames |
| 5. Association | `services/association` | Scene graph: rider→vehicle, helmet→rider |
| 6. Violation reasoning | `services/violation_reasoning` | Per-vehicle violations with reason + confidence |
| 7. OCR | `services/ocr` | Plate text, Indian format validation |
| 8. Evidence | `services/evidence` | Annotated image + `{media_id}_enforcement.json` |

### Review workflow states

| Status | Meaning |
|--------|---------|
| `pending_review` | AI proposal awaiting officer action |
| `confirmed` | Officer approved — eligible for challan export |
| `rejected` | Officer dismissed — feeds active learning |
| `auto_cleared` | Low confidence / no violation |

---

## Violation detection modules

Every violation is evaluated **per vehicle** in `services/violation_reasoning/vehicle_eval.py`, using thresholds from `CONTEXT/violation_rules.yaml`.

| Violation | Detection method | Key files |
|-----------|------------------|-----------|
| `helmet_non_compliance` | Helmet YOLO + CV heuristics on rider head ROI | `detection/helmet_yolo.py`, `violation_reasoning/helmet*.py` |
| `triple_riding` | Count seated adult riders on motorcycle (≥3) | `association/pose_rider.py`, `vehicle_eval.py` |
| `wrong_side_driving` | Motion angle vs `legal_direction_angle` (video) or bbox orientation (image) | `tracking/service.py`, `vehicle_eval.py` |
| `seatbelt_non_compliance` | Diagonal line detection on driver torso ROI | `vehicle_eval.py` |
| `illegal_parking` | Vehicle center inside `no_parking_zones` | `vehicle_eval.py` + scene config |
| `stop_line_violation` | Vehicle past `stop_line_y` when `signal_state=red` | `vehicle_eval.py` + scene config |
| `red_light_violation` | Vehicle center inside `intersection_roi` when light is red | `vehicle_eval.py` + scene config |

**License plates** are not a violation — OCR runs after violation detection in `services/ocr/service.py` and attaches plate text to each evidence record.

---

## Configuration reference

All settings use the `TV_` environment prefix (see `config.py`).

| Variable | Default | Description |
|----------|---------|-------------|
| `TV_API_PORT` | `8001` | API listen port |
| `TV_YOLO_MODEL` | `yolo11n.pt` | Ultralytics weights (auto-downloaded) |
| `TV_YOLO_CONFIDENCE` | `0.35` | Detection confidence threshold |
| `TV_USE_HELMET_YOLO` | `true` | Enable dedicated helmet model |
| `TV_HELMET_YOLO_MODEL` | `data/models/helmet_yolo.pt` | Helmet weights path |
| `TV_WARMUP_ENABLED` | `true` | Preload models on startup |
| `TV_WARMUP_BLOCKING` | `true` (local) | Block requests until models ready |
| `TV_DEMO_FALLBACK` | `false` | OpenCV detection for synthetic demo images |
| `TV_AUTH_ENABLED` | `false` | Enable JWT / API key auth |
| `TV_DATABASE_URL` | *(empty)* | PostgreSQL URL; empty = SQLite at `data/trafficvision.db` |
| `TV_REDIS_URL` | *(empty)* | Redis for distributed job queue |
| `VITE_API_URL` | *(empty)* | Frontend API origin (set on Vercel/Render; empty = Vite proxy) |

**Optional `.env` file** (project root, gitignored):

```env
TV_API_PORT=8001
TV_USE_HELMET_YOLO=true
TV_WARMUP_BLOCKING=true
```

---

## API reference

Base URL: `http://localhost:8001` (local) or your deployed API origin.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | App status, feature flags, `models_ready` |
| POST | `/api/v1/auth/token` | Get JWT (when auth enabled) |
| POST | `/api/v1/media/upload` | Upload image/video + scene config |
| POST | `/api/v1/media/rtsp` | Capture frame from RTSP stream |
| POST | `/api/v1/media/{media_id}/process` | Re-process existing media |
| GET | `/api/v1/jobs/{job_id}` | Job status & enforcement result |
| WS | `/api/v1/ws/jobs/{job_id}` | Real-time job progress events |
| GET | `/api/v1/evidence` | Search / filter evidence |
| PATCH | `/api/v1/evidence/{id}/review` | Confirm or reject |
| POST | `/api/v1/evidence/{id}/export-challan` | Generate challan receipt |
| GET | `/api/v1/analytics/summary` | Dashboard KPIs & trends |
| GET | `/api/v1/analytics/mobility` | Congestion & mobility metrics |
| GET | `/api/v1/metrics` | Latency p50/p95, throughput |
| GET | `/api/v1/feedback/stats` | Rejection feedback aggregates |
| GET | `/api/v1/queue/status` | Background job queue status |

Full interactive docs: **http://localhost:8001/docs**

### Bengaluru pilot cameras

Configured in `frontend/src/config/city.js`:

| Zone | Camera ID | Approx. location |
|------|-----------|------------------|
| MG Road | `CAM_BLR_MG_01` | 12.9750, 77.6063 |
| Silk Board | `CAM_BLR_SILK_01` | 12.9176, 77.6234 |
| Hebbal Flyover | `CAM_BLR_HEBBAL_01` | 13.0358, 77.5970 |
| Electronic City | `CAM_BLR_ECITY_01` | 12.8399, 77.6770 |
| Indiranagar | `CAM_BLR_INDIRA_01` | 12.9784, 77.6408 |

---

## Running tests

```bash
# From project root with venv activated
python -m pytest

# Verbose
python -m pytest -v

# Single module
python -m pytest tests/test_violations.py
```

Tests disable model warmup (`TV_WARMUP_ENABLED=false` via `conftest.py`) and use synthetic images — no GPU or real media required.

---

## Deployment

### Render (recommended — included blueprint)

The repo ships `render.yaml` and a `Dockerfile`.

1. Go to [render.com](https://render.com) → **New** → **Blueprint**
2. Connect your GitHub repo
3. Apply the blueprint — creates **nigha-ai-api** (Docker) + **nigha-ai-frontend** (static)
4. Wait for the API build (~10–15 min first time)
5. Verify: `https://<your-api>.onrender.com/health` → `"models_ready": true`
6. Open the frontend URL Render provides

**Notes:**

- API needs **Standard** plan (2 GB RAM) for YOLO + EasyOCR; Starter (512 MB) will OOM
- `VITE_API_URL` is wired automatically from the API service URL
- Render sets `TV_USE_HELMET_YOLO=false` and `TV_WARMUP_BLOCKING=false` for faster cold starts

### Docker (API only)

```bash
docker build -t nigha-ai-api .
docker run -p 8001:10000 -e PORT=10000 nigha-ai-api
```

Health: http://localhost:8001/health

### Vercel + ngrok (live demo from laptop)

For demos where the API runs on your machine:

1. `python run_server.py`
2. `ngrok http 8001`
3. Deploy frontend to Vercel with `VITE_API_URL=https://<your-ngrok-url>`

See `DEPLOY_LIVE.md` for demo URL update steps.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `models_ready: false` forever | Wait 2–3 min on first run; check `/health` for warmup error. Ensure ~2 GB RAM free |
| Frontend shows "Cannot reach backend" | Start API: `python run_server.py`. Confirm port 8001 is free |
| Port 8001 already in use | Windows: run `start_server.ps1` (kills existing process). Or change `TV_API_PORT` |
| `pip install` fails on Windows | Use Python 3.11, upgrade pip: `python -m pip install --upgrade pip` |
| Helmet detection inaccurate | Download helmet weights (Step 3 above), set `TV_USE_HELMET_YOLO=true` |
| Upload hangs / times out | First inference after warmup can take 30–60s on CPU — normal |
| Tests fail on import | Activate venv first: `.\.venv\Scripts\Activate.ps1` |
| CORS errors from Vercel/ngrok | API allows `*.vercel.app`, `*.onrender.com`, `*.ngrok*.app` by default |

---

## Related documents

| Document | Contents |
|----------|----------|
| [`SOLUTION.md`](SOLUTION.md) | Full solution write-up, differentiation, roadmap |
| [`CONTEXT/enforcement_spec.md`](CONTEXT/enforcement_spec.md) | Behavior contract for enforcement output |
| [`CONTEXT/violation_rules.yaml`](CONTEXT/violation_rules.yaml) | Violation thresholds & reason templates |
| [`DEPLOY_LIVE.md`](DEPLOY_LIVE.md) | Live demo URLs (Vercel + ngrok) |

---

## Summary

**Nigha AI** bridges scalable computer vision and accountable traffic enforcement. Every violation binds to a specific vehicle, ships with explainable evidence, and passes through human officer review — designed to move Indian cities from AI demos to defensible enforcement at scale, starting with **Bengaluru**.
