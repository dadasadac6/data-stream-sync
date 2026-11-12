#!/usr/bin/env bash
# Ecosystem Telemetry Dashboard Launcher
# Serves on http://localhost:8080 and LAN

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=========================================================="
echo "📊  Starting Ecosystem Telemetry Dashboard (FastAPI)..."
echo "=========================================================="
echo "Localhost: http://localhost:8080"
echo "=========================================================="

python3 -m uvicorn dashboard:app --host 0.0.0.0 --port 8080
