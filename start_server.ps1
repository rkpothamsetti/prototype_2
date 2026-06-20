# TrafficVision — safe server start (Windows)
$ErrorActionPreference = "Stop"
$Port = 8001
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "Stopping any process on port $Port..."
Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 2

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "Creating virtual environment..."
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
}

Write-Host "Starting TrafficVision API on port $Port..."
Write-Host "Keep this window open. Press Ctrl+C to stop."
.venv\Scripts\python.exe run_server.py
