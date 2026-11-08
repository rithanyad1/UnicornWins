# Connect the Pico, API, and dashboard

The supported live path is Pico → FastAPI → `/overview`. The dashboard calls
its own `/api/hardware` route, which fetches the FastAPI hardware snapshot on
the server. Browser CORS configuration is not required for that path. No
credentials are sent by the browser.

## Backend on Render

For the existing `un1c0rn-2` service, apply the settings in the root `render.yaml`
to that service. Importing a Blueprint may create another service: do not create
a duplicate if the existing one is already connected to this repository.

- Root directory: `backend`
- Build: `pip install .`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
- Health check: `/health`
- Environment: `APP_ENV=production`, `SIMULATION_ENABLED=false`
- Set explicit, distinct `PICO_DEVICE_TOKEN`, `ESP32_DEVICE_TOKEN`, and
  `OPERATOR_API_KEY` values in Render. Copy the Pico token to the board's
  `wifi_config.py` as `DEVICE_TOKEN`. Never use the development fallback in production.
- Copy `SPACETIMEDB_URI`, `SPACETIMEDB_DATABASE`, and `SPACETIMEDB_TOKEN` into
  Render's environment to enable persistence. The token must belong to the
  original database owner or an identity authorized by the module's
  `SENTINEL_BACKEND_IDENTITY` publishing environment value. Local `.env` files
  are ignored by Git and do not configure the deployment.
- Gemini is optional. It is not needed for hardware uploads or dashboard readings.

Keep one backend worker/instance because live state and command queues are held
in memory. A service that sleeps may miss the Pico's two-second socket timeout;
wake it before a demo. Continuous monitoring needs a service that remains running.
Increasing the firmware timeout also increases the time local monitoring can
pause during a request. These HTTP calls do not provide a hard real-time safety loop.

## Frontend hosting

Deploy `frontend` as a Next.js server application (for example, Vercel or a Node
web service), not a static export. Build with `npm ci` then `npm run build`;
on a Node web service start with `npm start -- --port $PORT`.

Set this **server** environment variable on the frontend host:

```dotenv
API_BASE_URL=https://un1c0rn-2.onrender.com
```

Redeploy after applying the changes. This is also the production default; local
development defaults to `http://127.0.0.1:8000`. `NEXT_PUBLIC_API_BASE_URL` remains
a compatibility fallback when `API_BASE_URL` is absent. For local use against
Render, copy `frontend/.env.example` to `frontend/.env.local` and restart Next.js.
Never put device, operator, database, or Gemini secrets in a `NEXT_PUBLIC_` variable.

If another client accesses FastAPI directly from a browser, set backend
`CORS_ORIGINS` to its exact HTTPS origin (comma-separated for multiple origins).

## Pico files

Install current Pico 2 W MicroPython, `ssd1306`, and a `requests` implementation
supporting `json` and `timeout`. Copy `main.py`, `telemetry_upload.py`,
`commands.py`, and the private `wifi_config.py` to the board. Use the HTTPS
backend URL above, reachable Wi-Fi, and the same Pico device token as Render.
Optional `HTTP_TIMEOUT_SECONDS` defaults to 2 for existing config files.

The Pico polls commands once per report cycle (approximately three seconds plus
sensor and network delays). `FAN_ON` holds the fan at 100%; `FAN_OFF` releases
that override only when the temperature is known and below the local warning
threshold (74 F by default). Local cooling protection remains active every loop.
The backend applies the same 74 F restriction to native Pico reports. If you
change firmware warning thresholds, update that backend guard too. Command
parameters and other actuators are rejected; no vent is wired in this program.
Failed acknowledgments are retried before another command is fetched.

Uploads refresh the controller heartbeat. Reports preserve Fahrenheit, vibration
in g, missing measurements, and local alerts. They are not converted to the ESP32
protocol, which has a water sensor and different vibration units. The ESP32
incident/AI pipeline and illustrative incident/map screens are separate from
the native Pico dashboard.

## Verify after deployment

1. Visit the backend `/health`: expect `{"status":"ok"}`.
2. Visit `/api/v1/system/status`: check `spacetimedb_status`. A healthy API alone
   does not prove database connectivity.
3. Restart the Pico. Expect `Backend report: saved` (database enabled) or
   `Backend report: memory only` (database disabled).
4. Visit backend `/api/v1/telemetry/hardware?limit=1`: expect a recent report and
   `connected: true` within the default 15-second freshness window.
5. Visit frontend `/api/hardware`: expect the same live snapshot. A JSON `error`
   indicates frontend-to-backend failure and is also shown on `/overview`.
6. Visit `/overview`: values should match the Pico; null sensor values stay null.
7. To test controls, use `POST /api/v1/commands` with `X-Operator-Key` and body
   `{"device_id":"sentinel-pico","command_type":"FAN_ON"}`. Inspect the command's
   acknowledgment in backend logs/events, then request `FAN_OFF` below 74 F.

Pico errors: **401** means token mismatch; **404** means wrong URL or old backend;
**422** means schema mismatch; **503** means missing production auth or failed
configured persistence. Check backend logs for the specific cause. No data is
queued on the Pico when uploads fail.
