# Nigha AI

Per-vehicle traffic enforcement for Indian cities. Upload traffic media, detect violations per vehicle (`VEH-001`, …), read Indian plates, and send explainable evidence to an officer review queue.

**Violations:** no helmet · triple riding · wrong-side · no seatbelt · illegal parking · stop line · red light

---

## Setup

**You need:** Python 3.10+, Node.js 18+, ~2 GB RAM

### 1. Clone & install

```bash
git clone https://github.com/rkpothamsetti/prototype_2.git
cd prototype_2
python -m venv .venv
```

**Windows**
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run backend (terminal 1)

```bash
python run_server.py
```

Wait for http://localhost:8001/health → `"models_ready": true` (1–3 min on first run).

### 3. Run frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

**Windows shortcut:** double-click `start.bat` to launch both.

---

## How to use

1. Open the dashboard → confirm **Backend connected**
2. **Upload** tab → pick an image or video → **Analyze**
3. **Evidence** tab → review cases → **Confirm** or **Reject**
4. **Dashboard** tab → see stats and Bengaluru hotspot map

API docs: http://localhost:8001/docs

---

## Project structure

```
prototype_2/
├── api/main.py              # FastAPI routes
├── config.py                # Settings (TV_* env vars)
├── run_server.py            # Start backend
├── services/
│   ├── pipeline.py          # Main orchestrator
│   ├── detection/           # YOLO + helmet model
│   ├── association/         # Link riders/drivers to vehicles
│   ├── violation_reasoning/ # Violation rules (vehicle_eval.py)
│   ├── ocr/                 # Indian plate OCR
│   ├── evidence/            # Annotated output
│   ├── analytics/           # Dashboard data
│   └── challan/             # Receipt export
├── frontend/                # React dashboard (Vite + Tailwind)
├── db/                        # SQLite models
├── CONTEXT/                   # Rules & specs
├── tests/                     # 70 pytest tests
└── data/                      # DB, uploads, evidence (auto-created)
```

---

## How violations are detected

All rules run in `services/violation_reasoning/vehicle_eval.py`.

| Violation | How |
|-----------|-----|
| No helmet | Helmet YOLO + head ROI analysis on motorcycle riders |
| Triple riding | 3+ seated adults on one bike |
| Wrong side | Vehicle direction vs `legal_direction_angle` |
| No seatbelt | Diagonal lines on driver torso |
| Illegal parking | Vehicle inside no-parking zone |
| Stop line / red light | Vehicle position vs scene rules |

Plate OCR runs after detection in `services/ocr/service.py`.

Rule thresholds: `CONTEXT/violation_rules.yaml`

---

## Pipeline

```
Upload → Preprocess → YOLO detect → Track (video) → Associate → Violations → OCR → Evidence
```

| Part | Tech |
|------|------|
| Backend | FastAPI · port **8001** |
| Frontend | React + Vite · port **5173** |
| ML | YOLOv11 · EasyOCR · OpenCV |
| Database | SQLite (`data/trafficvision.db`) |

---

## Tests

```bash
python -m pytest
```

---

## Config (optional)

Create a `.env` file in the project root:

```env
TV_API_PORT=8001
TV_USE_HELMET_YOLO=true
```

| Variable | Default | What it does |
|----------|---------|--------------|
| `TV_API_PORT` | `8001` | API port |
| `TV_USE_HELMET_YOLO` | `true` | Better helmet detection |
| `TV_WARMUP_BLOCKING` | `true` | Wait for models before serving |
| `VITE_API_URL` | empty | Set when deploying frontend (Vercel/Render) |

**Optional — helmet model** (better accuracy):

```bash
mkdir -p data/models
curl -fsSL -o data/models/helmet_yolo.pt \
  "https://huggingface.co/iam-tsr/yolov8n-helmet-detection/resolve/main/best.pt"
```

---

## Deploy

**Render** (easiest): connect repo → New Blueprint → use `render.yaml`. Needs Standard plan (2 GB RAM).

**Docker:**
```bash
docker build -t nigha-ai-api .
docker run -p 8001:10000 -e PORT=10000 nigha-ai-api
```

**Live demo from laptop:** run API locally + `ngrok http 8001` + deploy frontend to Vercel with `VITE_API_URL`. See `DEPLOY_LIVE.md`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Backend not reachable | Run `python run_server.py`, check port 8001 |
| `models_ready: false` | Wait 2–3 min on first run |
| Port 8001 in use | Run `start_server.ps1` (Windows) |
| Upload slow | Normal on CPU — first run takes 30–60s |

---

## More docs

- [`SOLUTION.md`](SOLUTION.md) — full solution write-up
- [`CONTEXT/enforcement_spec.md`](CONTEXT/enforcement_spec.md) — output format
- [`CONTEXT/violation_rules.yaml`](CONTEXT/violation_rules.yaml) — rule thresholds
