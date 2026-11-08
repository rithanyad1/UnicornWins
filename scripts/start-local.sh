#!/usr/bin/env bash
# Start the backend, the frontend, and the Pico serial bridge together.
# Usage: scripts/start-local.sh [--no-bridge]
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd "$root/backend" && exec uvicorn app.main:app --port 8000) & pids+=($!)
(cd "$root/frontend" && exec npm run dev) & pids+=($!)

if [[ "${1:-}" != "--no-bridge" ]]; then
  sleep 3
  python3 "$root/scripts/serial_bridge.py" & pids+=($!)
fi

echo "Backend http://127.0.0.1:8000  ·  Dashboard http://localhost:3000  ·  Ctrl+C stops everything"
wait
