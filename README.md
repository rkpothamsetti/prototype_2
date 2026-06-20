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

## Deploy frontend on Vercel

Vercel should build **only the React app** (not the Python API). Either:

- **Root directory:** `frontend` — Framework Preset: Vite, Output: `dist`  
- **Or** leave root as repo root — `vercel.json` at the root already points to `frontend/`

The FastAPI + ML backend cannot run on Vercel (use Railway, Render, a VM, etc.). After deploying the API, set in Vercel → **Environment Variables**:

`VITE_API_URL` = `https://your-api-host.com` (no trailing slash)
