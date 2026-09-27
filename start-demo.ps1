# Starts the Conduto demo locally: API on http://localhost:8000, web app on http://localhost:3000
# Usage (from this folder):  powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
Start-Sleep -Seconds 12
Start-Process "http://localhost:3000"
