#!/usr/bin/env bash
# 1-Click Dashboard Launcher for Autonomous Developer Search Gap Radar (Gold Miner)
# Serves on http://localhost:8080 and LAN http://192.168.100.75:8080

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=========================================================="
echo "⛏️  Starting Gold Miner Radar Dashboard (FastAPI)..."
echo "=========================================================="
echo "Localhost: http://localhost:8080"
echo "LAN:       http://192.168.100.75:8080"
echo "Budget:    \$0.00 Spend Hard Rule"
echo "=========================================================="

python3 -m uvicorn dashboard:app --host 0.0.0.0 --port 8080
