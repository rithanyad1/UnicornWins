# UN1C0RN^2 Pico 2 W

`main.py` runs the supplied DS18B20, DHT11, MPU6500, OLED, fan, LED,
and buzzer monitoring program. Every three seconds it prints a report and
posts the same JSON to `POST /api/v1/telemetry/hardware`.

1. Install MicroPython for the Pico 2 W and the `ssd1306` and `requests`
   modules (a recent version supporting the `timeout` argument).
2. Copy `wifi_config.example.py` to `wifi_config.py`. Set the Wi-Fi credentials,
   the backend computer's reachable LAN URL, and `DEVICE_TOKEN` to match
   `PICO_DEVICE_TOKEN` in `backend/.env`.
3. Copy `main.py`, `telemetry_upload.py`, `commands.py`, and your `wifi_config.py` to the Pico.
4. For Render, use `https://un1c0rn-2.onrender.com` and match the deployed
   `PICO_DEVICE_TOKEN`. For a local backend, bind to `0.0.0.0:8000` and allow
   the Pico to reach that port.

See [deployment setup](../../docs/deployment.md) for frontend hosting, Render
environment variables, and end-to-end verification. `sensors.py` is currently
an unused placeholder; sensor initialization and readings live in `main.py`.

The firmware polls commands every report cycle. `FAN_ON` holds the fan at 100%;
`FAN_OFF` releases that override only with a known temperature below 74 F.
Local fan protection always takes priority. Unsupported commands and parameters
are acknowledged as failed; no vent control is implemented. Lost acknowledgments
are retried without reexecuting the command during the same boot.

UN1C0RN^2 keeps the protocol device ID `SENTINEL-01`; the backend authenticates it
as its registered `sentinel-pico` controller. No backend secrets are embedded
in the firmware repository. The credentials file is ignored by Git.

Successful uploads print `saved` when SpacetimeDB persisted the report, or
`memory only` when the backend has no database configured. A configured
database failure returns 503. Upload failures are logged, the next report is
attempted on the next cycle, and Wi-Fi reconnection is attempted every 30 seconds.
Failed samples are not queued on the Pico. HTTP requests use a two-second
socket timeout and can delay sampling; the existing local fan and alert logic
continues between upload attempts.

Read recent reports at `GET /api/v1/telemetry/hardware?limit=100`.
The backend preserves Fahrenheit, vibration in g, null sensor readings,
hardware status, fan state, and exact alert reasons in SpacetimeDB's existing
`system_events` table (`HARDWARE_TELEMETRY`), broadcasts `hardware.telemetry`,
and updates the controller heartbeat. No database migration is required.
History is bounded by `TELEMETRY_HISTORY_LIMIT`; startup restores hardware
reports found among the most recent 1,000 system events within seven days.

The `/overview` dashboard reads this native history endpoint and displays null
values when the Pico is disconnected or its reports expire. The existing ESP32
`/telemetry` endpoint and backend safety engine continue to use the ESP32 format. The Pico report has no water sensor, and
its vibration units and local demonstration thresholds differ from that
format, so reports are not converted into synthetic ESP32 readings.
