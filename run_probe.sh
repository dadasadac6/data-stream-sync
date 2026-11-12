#!/usr/bin/env bash
# Ecosystem Telemetry Probe Daemon Launcher
# Continuous autonomous verification loop

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=========================================================="
echo "📡  Starting Ecosystem Telemetry Probe..."
echo "=========================================================="
echo "Protocol: 8-Term Batch Exploration + Matrix Verification"
echo "=========================================================="

python3 probe_daemon.py "$@"
