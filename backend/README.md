# UN1C0RN^2 backend

Safety-first FastAPI backend for environmental monitoring, command delivery, incident tracking, and simulated facilities.

## Requirements

- macOS with Python 3.11 or newer
- A SpacetimeDB database for persistence (optional for local development; requires the `spacetime` CLI and Node.js to publish the module)
- A Google Gemini API key from Google AI Studio (optional)

## 1. Create a Python environment

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
```

## 2. Configure environment variables

```bash
cp .env.example .env
```

Set the following values in `backend/.env`:

| Variable | Purpose |
|---|---|
| `APP_ENV` | Use `development` locally; production requires explicit credentials. |
| `HOST`, `PORT` | Uvicorn bind address and port. |
| `SPACETIMEDB_URI`, `SPACETIMEDB_DATABASE`, `SPACETIMEDB_TOKEN` | SpacetimeDB host (defaults to Maincloud), database name, and the owner identity's token. Backend-only; never put the token in the frontend. |
| `GEMINI_API_KEY`, `GEMINI_BASE_URL`, `GEMINI_MODEL` | Gemini API key, OpenAI-compatible endpoint (defaults to `https://generativelanguage.googleapis.com/v1beta/openai/`), and model (defaults to `gemini-3.8-flash`). |
| `GEMINI_ACTIONS_ENABLED` | Defaults to `false`; explicitly enable only after operator review. Requests still pass backend safety checks. |
| `ESP32_DEVICE_TOKEN`, `PICO_DEVICE_TOKEN` | Per-device authentication tokens. |
| `OPERATOR_API_KEY` | Authentication for manual commands, mode changes, model training, and simulation triggers. |
| `SIMULATION_ENABLED` | Run the three built-in simulated facilities alongside the real facility. |
| `HIGH_TEMP_THRESHOLD`, `CRITICAL_TEMP_THRESHOLD`, `RECOVERY_TEMP_THRESHOLD` | Temperature thresholds in Celsius. |
| `HIGH_HUMIDITY_THRESHOLD`, `VIBRATION_THRESHOLD` | Humidity and vibration alert thresholds. |
| `DEVICE_TIMEOUT_SECONDS` | Heartbeat timeout for device disconnect detection. |
| `TELEMETRY_PERSIST_INTERVAL_SECONDS` | Batch flush interval for routine readings. |
| `RECOVERY_STABILITY_SECONDS` | Required continuous recovery interval. |
| `ANOMALY_MODEL_PATH`, `ANOMALY_BASELINE_PATH` | Local Isolation Forest model and optional CSV baseline paths. |

If a token is blank in development, the local-only values are `dev-esp32-token`, `dev-pico-token`, and `dev-operator-token`. These are not accepted in non-development environments. Use unique secrets outside local development.

## 3. Set up SpacetimeDB (optional)

The database schema lives in the TypeScript module in [`spacetimedb/`](../spacetimedb/). See [spacetimedb/README.md](../spacetimedb/README.md) for the tables and conventions.

Install the SpacetimeDB CLI (see spacetimedb.com/install), log in, and publish the module from the repository root:

```bash
spacetime login
cd spacetimedb && npm install
spacetime publish sentinel            # Maincloud
# or, for a local server: spacetime start   (in another terminal)
#                         spacetime publish --server local sentinel
```

Publishing for the first time runs the module's `init` reducer. It seeds the four facilities and eight devices, and records the publishing identity as the database owner. All tables are private, and only that owner identity can write rows or read them over SQL. Give the backend the same identity's token:

```bash
spacetime login show --token
```

Then set `SPACETIMEDB_DATABASE=sentinel` and `SPACETIMEDB_TOKEN=<that token>` in `backend/.env`. Set `SPACETIMEDB_URI` to `http://127.0.0.1:3000` when using a local server. Without these values the API still runs from memory: routine telemetry is buffered and critical persistence failures are logged.

## 4. Configure Google Gemini (optional)

Create an API key in Google AI Studio and set `GEMINI_API_KEY`. `GEMINI_BASE_URL` and `GEMINI_MODEL` have working defaults; override `GEMINI_MODEL` to use a different Gemini model. The backend calls Gemini through its OpenAI-compatible chat-completions endpoint with bounded tool calls. The API continues with safety-rule decisions when Gemini is not configured or unavailable. Autonomous AI actions are disabled unless `GEMINI_ACTIONS_ENABLED=true`; AI cannot issue a command directly to hardware.

## 5. Start the API and simulator

From `backend/` with the virtual environment active:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

When `SIMULATION_ENABLED=true`, the server starts three labeled simulated facilities and sends synthetic telemetry through the same telemetry, incident, and safety pipeline. Simulated facilities never enqueue physical hardware commands.

Trigger a simulator scenario from another terminal:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/facilities/facility-sim-west/simulation/trigger \
  -H 'Content-Type: application/json' \
  -H 'X-Operator-Key: dev-operator-token' \
  -d '{"scenario":"overheating"}'
```

Available scenarios: `overheating`, `water`, `vibration`, `disconnect`, and `normal`.

## 6. Send a telemetry reading

```bash
curl -X POST http://127.0.0.1:8000/api/v1/telemetry \
  -H 'Content-Type: application/json' \
  -H 'X-Device-Token: dev-esp32-token' \
  -d '{
    "device_id":"sentinel-esp32",
    "temperature_c":26.4,
    "humidity_percent":45,
    "vibration_score":0.08,
    "water_detected":false,
    "timestamp_ms":15320
  }'
```

The server validates bounds and monotonic device sequence numbers, stamps the reading in UTC, updates in-memory state, broadcasts it, then runs the rule and anomaly paths. Invalid or stale readings return a 4xx response; authenticated sensor faults are recorded. Firmware may include an optional `boot_id` that changes after reboot to safely restart its uptime-based `timestamp_ms` counter.

## 7. Poll and acknowledge hardware commands

Pico command polling (repeat approximately every 250–500 ms):

```bash
curl http://127.0.0.1:8000/api/v1/devices/sentinel-pico/commands/next \
  -H 'X-Device-Token: dev-pico-token'
```

After physical execution, report the actual state:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/commands/COMMAND_UUID/ack \
  -H 'Content-Type: application/json' \
  -H 'X-Device-Token: dev-pico-token' \
  -d '{"status":"EXECUTED","reported_state":{"fan":true}}'
```

Use `FAILED` and include `failure_reason` when execution fails. Polling is repeatable and returns the same unacknowledged command; terminal acknowledgments are idempotent. Manual commands require `X-Operator-Key`, target a connected Pico, and are checked against the latest sensor state:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/commands \
  -H 'Content-Type: application/json' \
  -H 'X-Operator-Key: dev-operator-token' \
  -H 'Idempotency-Key: demo-fan-on-001' \
  -d '{"device_id":"sentinel-pico","command_type":"FAN_ON","parameters":{}}'
```

An `EXECUTED` acknowledgment is only accepted when the reported actuator state matches the command (for example, `fan: true` for `FAN_ON`). Cooling is latched on at the high-temperature threshold and an automatic `FAN_OFF` command is queued only after the lower recovery threshold is reached.

## 8. Useful endpoints

- `GET /health`
- `GET /api/v1/system/status`
- `GET /api/v1/sensors/latest`, `GET /api/v1/sensors/history`
- `GET /api/v1/facilities`, `GET /api/v1/facilities/{id}`
- `GET /api/v1/facilities/{id}/history`, `GET /api/v1/facilities/{id}/incidents`
- `GET /api/v1/network/overview`
- `GET /api/v1/incidents`, `GET /api/v1/incidents/{id}`, `GET /api/v1/decisions`
- `WS /ws/live`

Interactive API documentation: <http://127.0.0.1:8000/docs>

Train the anomaly model from development data, recent readings, or the configured baseline CSV:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/system/anomaly/train \
  -H 'Content-Type: application/json' \
  -H 'X-Operator-Key: dev-operator-token' \
  -d '{"source":"simulated"}'
```

The service does not use anomaly predictions until a trained model is available. Model scores are relative Isolation Forest scores, not calibrated failure probabilities. Safety thresholds always take priority.

## 9. Run tests

```bash
python -m pytest -q
```

Tests use in-memory state and mocks; no device, SpacetimeDB, or Gemini credentials are required. `tests/conftest.py` blanks those credentials so values in `.env` are never used.

## Troubleshooting

- **401 from a device endpoint:** Check the matching device token header and exact registered device ID.
- **409 on telemetry:** `timestamp_ms` must strictly increase for that device.
- **409 for a manual command:** The device may be disconnected or the action may conflict with current safety conditions.
- **`spacetimedb_status` is `not_configured`:** Set `SPACETIMEDB_DATABASE` and `SPACETIMEDB_TOKEN` and restart. Database outages are logged; buffered telemetry stays in process memory until a later flush.
- **Reducer fails with "Only the UN1C0RN^2 backend identity may write":** `SPACETIMEDB_TOKEN` belongs to a different identity than the one that published the database. Use the token from `spacetime login show --token` on the publishing machine.
- **Gemini unavailable:** Verify the API key in Google AI Studio and that `GEMINI_MODEL` is a model available to that key. Rule-based monitoring and emergency actions continue.
- **No anomaly results:** Train a model first. Training requires at least 20 baseline readings.
- **No telemetry from hardware:** Confirm the backend and MCU share network access, the device sends UTC-independent `timestamp_ms` values, and the token is configured on both sides.

## Hardware integration notes

- Configure the Pico to use the device token, heartbeat endpoint, 250–500 ms command polling, and acknowledgment endpoint.
- Send a heartbeat promptly after boot and report actuator state after each command.
- Firmware must independently force cooling on critical temperature and must not permit backend commands to override that local protection.
- Test actuator wiring and GPIO polarity before enabling automatic responses in a physical facility.
- The service-role key and operator key belong only on the backend. Use TLS and rotate device/operator tokens before deployment.
- The in-memory queue/state is intentionally resilient to an external database outage but is not durable across a backend process restart. Use a persistent message queue for deployments that require restart-safe buffering.

## Pico 2 W native hardware reports

The supplied `SENTINEL-01` program uploads to `POST /api/v1/telemetry/hardware`
using `X-Device-Token` matching `PICO_DEVICE_TOKEN`. Reports preserve Fahrenheit,
vibration in g, nullable sensor values, local status, fan state, and alert reasons.
They are saved in the existing SpacetimeDB `system_events` JSON metadata under
`HARDWARE_TELEMETRY` and published over WebSocket as `hardware.telemetry`.

`GET /api/v1/telemetry/hardware?limit=100` returns recent reports, oldest first.
Responses to uploads include `persisted`: false means the database is not
configured and the report is held in memory only. A configured database write
failure returns 503. These reports feed the `/overview` dashboard. The history
response includes `connected`, `device_timeout_seconds`, and `checked_at` so
the dashboard can clear stale values. They do not feed the ESP32 safety rules. See [Pico setup](../firmware/pico/README.md)
for firmware installation and network configuration.
