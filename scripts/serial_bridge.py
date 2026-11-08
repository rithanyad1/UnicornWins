#!/usr/bin/env python3
"""Forward the SENTINEL Pico 2 W's live reports to the backend.

The node firmware prints one JSON report per line on its USB serial port
(``print(json.dumps(payload))``) among other human-readable lines. This bridge
reads that port, picks out the JSON reports, and POSTs each one unchanged to
``/api/v1/hardware/report``. The firmware does not need any changes.

Usage:
    pip install pyserial
    python scripts/serial_bridge.py                      # auto-detect the Pico
    python scripts/serial_bridge.py --port /dev/ttyACM0  # or COM3 on Windows
    python scripts/serial_bridge.py --stdin < capture.txt   # replay a saved log

Close Thonny (or any other serial monitor) first: only one program can hold the port.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Iterable, Iterator

PICO_USB_VENDOR_ID = 0x2E8A  # Raspberry Pi
REQUIRED_KEYS = {"device_id", "temperature_f", "humidity_percent", "vibration_g", "status"}


def parse_report(line: str) -> dict | None:
    """Return the report if this serial line is one of the firmware's JSON reports."""
    line = line.strip()
    if not line.startswith("{"):
        return None
    try:
        report = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(report, dict) or not REQUIRED_KEYS <= report.keys():
        return None
    return report


def post_report(backend: str, token: str, report: dict, timeout: float = 5.0) -> tuple[int, str]:
    request = urllib.request.Request(
        f"{backend.rstrip('/')}/api/v1/hardware/report",
        data=json.dumps(report).encode(),
        headers={"Content-Type": "application/json", "X-Device-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")


def find_pico_port() -> str | None:
    from serial.tools import list_ports

    ports = list(list_ports.comports())
    for port in ports:
        if port.vid == PICO_USB_VENDOR_ID:
            return port.device
    return None


def serial_lines(port: str | None, baud: int) -> Iterator[str]:
    """Yield lines from the Pico, reconnecting if it is unplugged or reset."""
    import serial

    while True:
        device = port or find_pico_port()
        if device is None:
            print("Waiting for the Pico to be plugged in over USB...", file=sys.stderr)
            time.sleep(3)
            continue
        try:
            with serial.Serial(device, baud, timeout=1) as connection:
                print(f"Reading SENTINEL node on {device}", file=sys.stderr)
                while True:
                    raw = connection.readline()
                    if raw:
                        yield raw.decode(errors="replace")
        except serial.SerialException as exc:
            print(f"Serial connection lost ({exc}); retrying in 3 s", file=sys.stderr)
            time.sleep(3)


def run(lines: Iterable[str], backend: str, token: str, echo: bool) -> None:
    for line in lines:
        if echo:
            print(line.rstrip(), file=sys.stderr)
        report = parse_report(line)
        if report is None:
            continue
        try:
            status, body = post_report(backend, token, report)
        except (urllib.error.URLError, OSError) as exc:
            print(f"Backend unreachable at {backend}: {exc}", file=sys.stderr)
            continue
        if status == 202:
            print(
                f"sent {report['device_id']}: {report.get('temperature_f')} F, "
                f"{report.get('humidity_percent')} %, {report.get('vibration_g')} g, {report.get('status')}"
            )
        else:
            print(f"Backend rejected report ({status}): {body}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", help="Serial port of the Pico (default: auto-detect)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--backend", default=os.environ.get("SENTINEL_BACKEND_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--token", default=os.environ.get("SENTINEL_DEVICE_TOKEN") or "dev-sentinel-token")
    parser.add_argument("--stdin", action="store_true", help="Read lines from standard input instead of serial")
    parser.add_argument("--echo", action="store_true", help="Also print every line the Pico prints")
    args = parser.parse_args()

    lines = sys.stdin if args.stdin else serial_lines(args.port, args.baud)
    try:
        run(lines, args.backend, args.token, args.echo)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
