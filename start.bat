@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
echo Starting TrafficVision API on http://localhost:8001
start "TrafficVision API" cmd /k python run_server.py
cd frontend
echo Starting Dashboard on http://localhost:5173
start "TrafficVision UI" cmd /k npm run dev
echo.
echo API:       http://localhost:8001/docs
echo Dashboard: http://localhost:5173
echo.
echo NOTE: If port 8000 has another app, TrafficVision uses 8001.
