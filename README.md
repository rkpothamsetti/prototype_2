# Nigha AI

Per-vehicle traffic enforcement platform for Indian cities. Upload CCTV or traffic images, detect violations per vehicle, OCR plates, and let officers review evidence before any challan is issued.

---

## Problem we are solving

Indian cities produce huge volumes of traffic footage every day, but police cannot manually review all of it. Simple “AI challan” tools also fail because they label whole images instead of answering:

1. **Which vehicle** broke the rule?
2. **What rule** was broken, and **why**?
3. **Can an officer defend** this in a dispute?

Nigha AI processes each vehicle separately (`VEH-001`, …), attaches explainable evidence (plate, violation type, confidence, bounding boxes), and routes cases to an officer review queue — AI proposes, humans decide.

---

## Prerequisites

- **Python** 3.10+  
- **Node.js** 18+

---

## Backend setup

```bash
cd prototype_2          # or your clone folder
python -m venv .venv
```

**Windows**

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_server.py
```

**macOS / Linux**

```bash
source .venv/bin/activate
pip install -r requirements.txt
python run_server.py
```

API runs at **http://localhost:8001** (docs: http://localhost:8001/docs).

First startup loads YOLO and OCR models; allow 1–2 minutes on CPU before uploading.

---

## Frontend setup

Open a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

Dashboard: **http://localhost:5173**

The frontend proxies API calls to the backend on port **8001**. Keep both terminals running.

---

## Windows shortcut

```cmd
start.bat
```

Starts the API and dashboard in separate windows.

---

## Deploy on Render

The repo includes `render.yaml` (API + frontend) and a `Dockerfile` for the ML backend.

1. Go to [render.com](https://render.com) → **New** → **Blueprint**
2. Connect **GitHub** → repo `rkpothamsetti/prototype_2`
3. Apply the blueprint (creates **nigha-ai-api** + **nigha-ai-frontend**)
4. Wait for the API build (~10–15 min first time). Open `https://nigha-ai-api.onrender.com/health` → `models_ready: true`
5. Open the frontend URL Render gives you (e.g. `https://nigha-ai-frontend.onrender.com`)

**Notes:** API uses **Starter** plan in `render.yaml` (ML models need more RAM than free tier). `VITE_API_URL` is set automatically from the API URL.
