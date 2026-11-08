#!/usr/bin/env bash
# Start the backend and the dashboard together.
# The backend listens on all interfaces so the Pico can reach it over Wi-Fi.
# Usage: scripts/start-local.sh [--usb-bridge]
#   --usb-bridge  also forward reports from a Pico plugged into this computer over USB
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd "$root/backend" && exec uvicorn app.main:app --host 0.0.0.0 --port 8000) & pids+=($!)
(cd "$root/frontend" && exec npm run dev) & pids+=($!)

if [[ "${1:-}" == "--usb-bridge" ]]; then
  sleep 3
  python3 "$root/scripts/serial_bridge.py" & pids+=($!)
fi

echo "Dashboard http://localhost:3000  ·  Pico should post to http://<this laptop's IP>:8000/api/sensor-data  ·  Ctrl+C stops everything"
wait
