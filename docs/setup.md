# Running SENTINEL over a phone hotspot

The Pico 2 W sends its readings over Wi-Fi to the backend on a teammate's laptop. The USB cable to your own laptop is only for power and Thonny.

```
Pico 2 W ── Wi-Fi (phone hotspot) ── POST /api/sensor-data ──▶ backend on the laptop ── /ws/live ──▶ dashboard
```

## 1. Join the same hotspot

Connect the Pico (already done through `wifi_config.py`) and the laptop that runs the backend to the **same** phone hotspot.

Some hotspots stop connected devices from talking to each other ("client isolation"). If step 5 below never shows readings, try another phone or a regular Wi-Fi router.

## 2. Start the backend and dashboard on the laptop

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env
cd ..
scripts/start-local.sh
```

On Windows, run the two parts in separate terminals instead:

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
cd frontend && npm install && npm run dev
```

`--host 0.0.0.0` matters: without it the backend only accepts connections from the laptop itself, and the Pico cannot reach it.

## 3. Find the laptop's IP address

- **Windows:** open Command Prompt, run `ipconfig`, and read the **IPv4 Address** under the Wi-Fi adapter (for example `172.20.10.3`).
- **Mac:** System Settings → Wi-Fi → Details → TCP/IP → IP address.

Check it from the laptop's browser: `http://<that IP>:8000/health` should show `{"status":"ok"}`.

## 4. Let port 8000 through the firewall

- **Windows:** the first time uvicorn starts, Windows asks whether Python may communicate on networks; allow it on **Private** and **Public** networks (hotspots are often marked Public). If you missed the prompt: Windows Security → Firewall & network protection → Allow an app through firewall → tick Python for both.
- **Mac:** System Settings → Network → Firewall. Either turn it off for the demo or allow incoming connections for Python.

From your phone's browser (it is on the hotspot too), `http://<laptop IP>:8000/health` should load. If it does, the Pico can reach the backend.

## 5. Add the send step to the Pico code

The backend accepts the Pico's existing `generate_payload()` JSON as is, so the Pico only needs to post it. Add these lines to `main.py` in Thonny:

At the top, with the other imports:

```python
import urequests
```

Under `DEVICE_ID = "SENTINEL-01"` (use the laptop's real IP):

```python
BACKEND_URL = "http://172.20.10.3:8000/api/sensor-data"
```

Above the main `while True:` loop:

```python
def send_to_backend(payload):
    if not wifi.isconnected():
        print("Wi-Fi disconnected")
        return
    try:
        response = urequests.post(BACKEND_URL, json=payload, timeout=3)
        print("Backend response:", response.status_code)
        response.close()
    except Exception as e:
        print("Backend connection error:", e)
```

In the report block, right after `payload = generate_payload(...)`:

```python
            send_to_backend(payload)
```

If `import urequests` fails, install it in Thonny: Tools → Manage packages → search `requests` (micropython-lib) → install, then use `import requests as urequests`.

A `Backend response: 202` line in Thonny means the reading arrived. Open `http://localhost:3000` on the laptop to see it on the dashboard.

The fan, LEDs and buzzer still run on the Pico itself, so cooling keeps working even when Wi-Fi drops.

## Viewing the dashboard from another device

The dashboard calls the backend on port 8000 of whatever host served it, so a phone on the hotspot can open `http://<laptop IP>:3000`. Add that origin to `CORS_ORIGINS` in `backend/.env` first, for example:

```
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://172.20.10.3:3000
```

## Security

With `APP_ENV=development` and no `SENTINEL_DEVICE_TOKEN`, `/api/sensor-data` accepts reports without a token, because `urequests.post()` sends none. That is fine on a private hotspot for a demo. To lock it down, set `SENTINEL_DEVICE_TOKEN` in `backend/.env` and add `headers={"X-Device-Token": "<the same value>"}` to the `urequests.post()` call.

## Fallback: USB instead of Wi-Fi

If the hotspot blocks device-to-device traffic, plug the Pico into the laptop that runs the backend, close Thonny, and run `pip install pyserial` then `scripts/start-local.sh --usb-bridge`. `scripts/serial_bridge.py` reads the reports the Pico already prints over USB, so no Pico changes are needed for this path.
