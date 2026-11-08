# UN1C0RN^2 (UnicornWins)

UN1C0RN^2 is a safety-first environmental monitoring system for small equipment rooms. An ESP32 reads temperature, humidity, vibration, and water sensors. A Raspberry Pi Pico drives the fan, vent, buzzer, and status LED. A FastAPI backend sits between them: it takes in telemetry, applies safety rules, opens incidents, queues hardware commands, and checks that conditions actually recover.

An Isolation Forest model and an optional Google Gemini agent add analysis on top. Neither one can bypass the deterministic safety rules.

## Project status

| Area | Status |
|---|---|
| `backend/` | Implemented. FastAPI service with 28 passing tests. |
| `spacetimedb/` | Implemented. TypeScript SpacetimeDB module with tables, seed data, and owner-only write reducers. |
| `frontend/` | Next.js dashboard. `/overview` displays live native Pico reports; incident and map screens include illustrative data. |
| `firmware/pico` | MicroPython sensor monitoring, telemetry uploads, and protected fan command polling. |
| `firmware/esp32` | Scaffolded; not required for the native Pico dashboard. |
| `scripts/` | Scaffolded only (files are empty). |
| `docs/` | Includes [deployment setup](docs/deployment.md); some other documents remain placeholders. |

## Architecture

```
                                       ┌───────────────────────┐
 ESP32 sensor ── POST telemetry ─────▶ │    FastAPI backend    │ ──▶ SpacetimeDB (optional)
                                       │                       │
 Pico control ── POST heartbeat ─────▶ │  Runtime (in-memory)  │ ──▶ Google Gemini (optional)
              ◀─ GET commands/next ─── │  ├ SafetyEngine       │
              ── POST commands/ack ──▶ │  ├ CommandManager     │
                                       │  ├ RecoveryVerifier   │
 Operator UI  ── REST ───────────────▶ │  ├ AnomalyDetector    │
              ◀─ WS /ws/live ───────── │  └ FacilitySimulator  │
                                       └───────────────────────┘
```

### Request flow for one reading

1. **Ingest:** `POST /api/v1/telemetry` authenticates the device token, checks value bounds, and requires `timestamp_ms` to strictly increase per device. A changed `boot_id`, or a reset after a timeout, is allowed. Rejected or invalid payloads from an authenticated device are recorded as `SENSOR_VALIDATION_FAULT` events.
2. **Safety rules:** `SafetyEngine` evaluates the reading against configured thresholds. When it triggers, the backend opens an incident and queues an idempotent command for the Pico:

   | Condition | Incident | Severity | Command |
   |---|---|---|---|
   | temp ≥ critical (104 °F) | `CRITICAL_TEMPERATURE` | CRITICAL | `FAN_ON` |
   | temp ≥ high (95 °F) | `HIGH_TEMPERATURE` | WARNING | `FAN_ON` (latched) |
   | temp ≤ recovery (89.6 °F), fan latched | (none) | — | `FAN_OFF` |
   | humidity ≥ 70 % | `HIGH_HUMIDITY` | WARNING | — |
   | water detected | `WATER_DETECTED` | CRITICAL | `BUZZER_ON` |
   | vibration ≥ 0.7 | `ABNORMAL_VIBRATION` | WARNING | `BUZZER_ON` |

   Cooling uses hysteresis. The fan latches on at the high threshold and is released only after the temperature drops below the lower recovery threshold.
3. **Recovery verification:** An incident resolves only after its condition has stayed recovered continuously for `RECOVERY_STABILITY_SECONDS`.
4. **Anomaly detection:** If a model has been trained, an Isolation Forest scores five features: temperature, humidity, vibration, and the rate of change of temperature and humidity. A flagged reading is recorded as an `ISOLATION_FOREST` decision. It is advisory only.
5. **Broadcast:** Every state change is pushed to WebSocket clients on `/ws/live`.

### Command lifecycle

`PENDING → DELIVERED → EXECUTED | FAILED`. A command that is not acknowledged within `command_ttl_seconds` (30 s) becomes `EXPIRED`.

- The Pico polls `GET /devices/{id}/commands/next`. Polling repeatedly returns the same unacknowledged command.
- An `EXECUTED` acknowledgment is accepted only if `reported_state` matches the command (for example `{"fan": true}` for `FAN_ON`). Otherwise the backend records the command as `FAILED`.
- Terminal acknowledgments are idempotent. Manual commands can be deduplicated with an `Idempotency-Key` header.
- Manual operator commands are rejected when they would conflict with current conditions. Examples: turning the fan off while the temperature is high, closing the vent while it is hot, or silencing the alarm while water is detected.

### AI layers and their limits

- **Isolation Forest** (`app/ai/anomaly_detector.py`) produces relative anomaly scores. They are not calibrated probabilities, and the model only runs after it has been trained via `POST /system/anomaly/train`.
- **Gemini agent** (`app/ai/gemini_agent.py`) runs when an incident is created, calling Gemini through its OpenAI-compatible endpoint. It has read-only tools plus `request_safe_action`, and it is limited to 4 rounds and 8 tool calls. Actions are refused unless `GEMINI_ACTIONS_ENABLED=true`, the system is in `AUTOMATIC` mode, the facility is physical, the action is on the allowlist (`FAN_ON`, `VENT_OPEN`, `BUZZER_ON`), and the safety engine approves it.

### Simulation

With `SIMULATION_ENABLED=true`, three simulated facilities (West, Central, East) generate synthetic telemetry once per second through the same pipeline. Operators can trigger the `overheating`, `water`, `vibration`, `disconnect`, or `normal` scenarios. Simulated facilities never queue physical hardware commands.

### Persistence and resilience

All live state is held in memory in `Runtime`, so the API keeps working when SpacetimeDB is unreachable or not configured.

- Routine readings are buffered (up to 10,000) and flushed in batches every `TELEMETRY_PERSIST_INTERVAL_SECONDS`.
- Incidents, commands, decisions, and events are written immediately. If a write fails, the failure is logged.
- On startup, recent state is reloaded from SpacetimeDB: facilities and devices in full, readings from the last day, and everything else from the last 7 days.
- The in-memory buffer does not survive a process restart.

## Repository layout

```
backend/
  app/
    main.py              App factory, lifespan (monitor + simulator tasks), CORS
    core/                Settings (pydantic-settings), token auth
    api/v1/              REST routes: telemetry, devices, commands, incidents,
                         decisions, sensors, system, facilities
    services/runtime.py  Central orchestrator: state, ingest, safety, recovery
    services/            Safety rules, command manager, persistence, simulator, monitor
    ai/                  Isolation Forest, features, explanations, Gemini agent
    db/                  SpacetimeDB HTTP client and row mapping
    realtime/            WebSocket connection manager and /ws/live route
    schemas/             Pydantic request models and enums
  tests/                 pytest suite (in-memory, no external services)
spacetimedb/             SpacetimeDB module (src/index.ts): tables, seed, reducers
frontend/, firmware/, scripts/, docs/   Placeholders
```

## Quick start (backend)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Interactive API docs are at <http://127.0.0.1:8000/docs>. Run the tests with `python -m pytest -q`.

In development, blank tokens fall back to `dev-esp32-token`, `dev-pico-token`, and `dev-operator-token`. These fallbacks are rejected when `APP_ENV` is anything other than `development`.

[backend/README.md](backend/README.md) covers the full setup: environment variables, SpacetimeDB, Gemini, curl examples for every device flow, and troubleshooting.

## Authentication

| Header | Used by |
|---|---|
| `X-Device-Token` | ESP32 telemetry; Pico heartbeat, command poll, and ack |
| `X-Operator-Key` | Manual commands, mode changes, model training, and simulation triggers |

Read-only `GET` endpoints and `/ws/live` are currently unauthenticated.

## Known gaps

- Read endpoints and the WebSocket have no authentication.
- State and the reading buffer are in memory, so the backend runs as a single process and loses its queue on restart.
- Device identities (`sentinel-esp32`, `sentinel-pico`) are hard-coded in auth and telemetry routing.
- Anomaly explanation thresholds in `app/ai/explanations.py` are hard-coded and do not follow `Settings`.
- `IncidentManager`, `event_logger.log_event`, `api/dependencies.get_app_runtime`, and several Pydantic response models are not used anywhere.
- `PUT /system/mode` takes `mode` as a query parameter, not in the request body.
