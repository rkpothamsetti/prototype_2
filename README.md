# Nigha AI

**Automated per-vehicle traffic enforcement platform** — upload traffic images or video, detect violations, OCR Indian plates, generate explainable evidence, and review cases in an officer dashboard.

> AI proposes. Officers decide. Every violation is attributable, explainable, and auditable.

---

## What you get

| Layer | Stack |
|-------|--------|
| **Frontend** | React, Vite, Tailwind, Recharts, Leaflet |
| **Backend** | FastAPI, SQLAlchemy, OpenCV |
| **CV / ML** | YOLOv11 (Ultralytics), EasyOCR, optional helmet YOLO |
| **Database** | SQLite (default); PostgreSQL optional |

**Dashboard:** http://localhost:5173  
**API docs:** http://localhost:8001/docs  
**Health check:** http://localhost:8001/health

---

## Prerequisites

Install these before you start:

| Requirement | Version | Notes |
|-------------|---------|--------|
| **Python** | 3.10 – 3.12 recommended | `python --version` |
| **Node.js** | 18+ (20 LTS ideal) | For the React dashboard |
| **npm** | Comes with Node | `npm --version` |
| **Git** | Any recent version | To clone the repo |
| **Disk space** | ~2 GB free | Models + Python deps |
| **RAM** | 8 GB+ recommended | First inference loads YOLO + OCR |

**Optional:** Redis (only if you enable the job queue in production-style setups).

**Network:** First run downloads YOLO weights (~6 MB) and EasyOCR models. Helmet model download is optional (see below).

---

## Quick start (5 minutes)

### 1. Clone and enter the project

```bash
git clone <your-repo-url> nigha-ai
cd nigha-ai
```

If you already have the folder, just `cd` into it.

### 2. Backend setup

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_server.py
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_server.py
```

The API starts on **port 8001**. On first startup it **warms up** YOLO and EasyOCR (can take 1–3 minutes on CPU). Wait until you see the server ready, or check:

```bash
curl http://localhost:8001/health
```

Look for `"models_ready": true` in the JSON response.

### 3. Frontend setup (new terminal)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

### 4. Try the app

1. Go to **Upload** → pick a traffic image (`CONTEXT/examples/sample_input/` has samples).
2. Submit → processing runs in the background.
3. Open **Evidence** → confirm or reject violations, issue e-Challan.
4. Open **Dashboard** / **Mobility** for analytics.

---

## One-click start (Windows)

**API only** (frees port 8001, creates venv if missing):

```powershell
.\start_server.ps1
```

**API + dashboard** (opens two terminal windows):

```cmd
start.bat
```

Then open http://localhost:5173.

---

## Optional: pre-load demo data

Skip the wait during demos by seeding the database with processed hero images:

```bash
# Activate venv first
python scripts/generate_hero_images.py   # creates Bengaluru-style demo images
python scripts/seed_demo.py              # runs pipeline + fills DB (~2–5 min CPU)
```

After seeding, the **Dashboard** and **Evidence** tabs show data immediately.

Generate synthetic test images only:

```bash
python scripts/generate_samples.py
```

---

## Optional: helmet detection model

Helmet violations use a dedicated YOLO model. If missing, the app falls back to heuristics.

```bash
python scripts/download_helmet_model.py
```

Saves to `data/models/helmet_yolo.pt` (~6 MB from Hugging Face).

---

## Environment variables

All settings use the `TV_` prefix. None are required for local development.

| Variable | Default | Description |
|----------|---------|-------------|
| `TV_API_PORT` | `8001` | API port |
| `TV_WARMUP_ENABLED` | `true` | Preload models on startup |
| `TV_WARMUP_BLOCKING` | `true` | Block requests until warmup finishes |
| `TV_DEMO_FALLBACK` | `false` | Synthetic detections when models fail |
| `TV_AUTH_ENABLED` | `false` | JWT / API-key auth |
| `TV_API_KEY` | `nigha-demo-key` | API key when auth enabled |
| `TV_DATABASE_URL` | *(empty)* | PostgreSQL URL; empty = SQLite |
| `TV_REDIS_URL` | *(empty)* | Redis for job queue; empty = inline |
| `TV_USE_HELMET_YOLO` | `true` | Use helmet YOLO weights |

**Example — disable warmup for faster test startup:**

```bash
# Windows PowerShell
$env:TV_WARMUP_ENABLED = "false"

# macOS / Linux
export TV_WARMUP_ENABLED=false
python run_server.py
```

---

## Running tests

```bash
# From project root, with venv active
pytest tests/ -v
```

For faster test runs (skip model warmup):

```bash
TV_WARMUP_ENABLED=false pytest tests/ -q
```

**Evaluation scripts:**

```bash
python scripts/evaluate.py
python scripts/eval_gridlock.py    # writes reports/eval_results.json
```

---

## Project structure

```
├── api/main.py              # FastAPI app & routes
├── config.py                # Settings (TV_* env vars)
├── schemas.py               # Pydantic models
├── run_server.py            # Start API (uvicorn)
├── services/                # CV pipeline modules
│   ├── pipeline.py          # Orchestrator
│   ├── detection/           # YOLO + helmet
│   ├── ocr/                 # EasyOCR + plate validation
│   ├── violation_reasoning/ # Per-vehicle rules
│   └── evidence/            # Annotated output + video
├── db/                      # SQLAlchemy models + SQLite
├── frontend/                # React dashboard (Vite)
├── CONTEXT/                 # Rules, schemas, sample images
│   ├── violation_rules.yaml
│   ├── enforcement_spec.md
│   └── examples/sample_input/
├── data/                    # Runtime data (created on first run)
│   ├── uploads/
│   ├── evidence/
│   └── trafficvision.db
├── scripts/                 # Seed, eval, sample generation
├── tests/                   # pytest suite
└── SOLUTION.md              # Full product / architecture doc
```

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | App status + `models_ready` |
| POST | `/api/v1/media/upload` | Upload image/video |
| GET | `/api/v1/jobs/{job_id}` | Job status & results |
| GET | `/api/v1/evidence` | List / search evidence |
| PATCH | `/api/v1/evidence/{id}/review` | Confirm / reject |
| POST | `/api/v1/evidence/{id}/export-challan` | Issue e-Challan |
| GET | `/api/v1/analytics/summary` | Dashboard stats |
| GET | `/api/v1/analytics/mobility` | Congestion / mobility |
| GET | `/api/v1/metrics` | Latency & quality metrics |
| WS | `/api/v1/ws/jobs/{job_id}` | Live job progress |

Interactive docs: http://localhost:8001/docs

---

## Upload form (scene configuration)

| Field | Purpose |
|-------|---------|
| `latitude` / `longitude` | Camera GPS |
| `camera_id` | Camera identifier |
| `legal_direction_angle` | Expected flow direction (wrong-side detection) |
| `no_parking_zones` | JSON `[[x1,y1,x2,y2], ...]` |
| `stop_line_y` | Stop line Y pixel (with red signal) |
| `traffic_light_state` | `red` / `green` / `unknown` |

Sample images: `CONTEXT/examples/sample_input/`

---

## Violation types

- Helmet non-compliance  
- Triple riding  
- Wrong-side driving  
- Illegal parking  
- Seatbelt non-compliance  
- Stop-line violation  
- Red-light violation  

Each violation binds to a **vehicle ID** (`VEH-001`, …), not the whole image.

---

## Troubleshooting

### `Backend offline` or red status in sidebar

1. Confirm API is running: `curl http://localhost:8001/health`
2. Start API: `python run_server.py`
3. Restart frontend: `cd frontend && npm run dev`

### Upload fails with `proxy error` / `ECONNREFUSED` / `ECANCELED`

The dashboard proxies API calls to **port 8001** (not 8000). Ensure:

- API is on 8001 (`config.py` / `TV_API_PORT`)
- `frontend/vite.config.js` targets `http://localhost:8001`

### `models_ready: false` for a long time

Normal on first start — YOLO + EasyOCR are loading. CPU can take 1–3 minutes. Refresh `/health` until `models_ready` is `true`.

### First upload is slow (~15–30 s)

Models may still be loading, or first inference is warming GPU/CPU caches. Subsequent uploads are faster.

### `pip install` fails on Windows

- Use **Python 3.10–3.12** from python.org (not deprecated 3.13-only wheels edge cases).
- Upgrade pip: `python -m pip install --upgrade pip`
- If OpenCV fails, try: `pip install opencv-python-headless`

### Port already in use

**Windows:**

```powershell
.\start_server.ps1   # kills process on 8001 and restarts
```

**macOS / Linux:**

```bash
lsof -ti:8001 | xargs kill -9
python run_server.py
```

### Frontend port 5173 in use

Vite will offer the next port (5174). Use that URL, or stop the other process.

### Helmet detection seems weak

Run `python scripts/download_helmet_model.py` and restart the API.

### Empty dashboard after fresh install

Run demo seed (see above) or upload at least one image via the **Upload** tab.

### SQLite / permission errors on `data/`

The app creates `data/` on startup. Ensure the project folder is writable (avoid read-only copies from zip tools).

---

## Production build (frontend only)

```bash
cd frontend
npm run build      # output in frontend/dist/
npm run preview    # local preview of production build
```

By default the dev server proxies `/api` to the backend. For a static deploy, configure your host to proxy API routes to the FastAPI service.

---

## Regenerate marketing screenshots

With API + frontend running:

```bash
pip install playwright
playwright install chromium
python scripts/capture_root_screenshots.py
```

Writes PNGs to the project root (dashboard, mobility, upload, evidence, challan views).

---

## Further reading

- **SOLUTION.md** — product narrative, architecture, Bangalore config, roadmap  
- **CONTEXT/enforcement_spec.md** — evidence JSON contract  
- **CONTEXT/violation_rules.yaml** — rule definitions  

---

## License / use

Hackathon and educational use. Not legal advice; enforcement workflows require human review and local regulations.
