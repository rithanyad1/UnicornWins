"""Bounded HTTP uploads; monitoring continues when Wi-Fi/backend is unavailable."""

from time import ticks_ms, ticks_diff

try:
    import requests
except ImportError:
    import urequests as requests

_last_reconnect = None


def send_report(wifi, payload, backend_url, token, ssid, password):
    global _last_reconnect
    response = None
    try:
        if not wifi.isconnected():
            now = ticks_ms()
            if _last_reconnect is None or ticks_diff(now, _last_reconnect) >= 30000:
                _last_reconnect = now
                wifi.connect(ssid, password)
            print("Backend upload skipped: Wi-Fi disconnected")
            return False

        response = requests.post(
            backend_url.rstrip("/") + "/api/v1/telemetry/hardware",
            json=payload,
            headers={"X-Device-Token": token},
            timeout=2,
        )
        if response.status_code != 202:
            print("Backend rejected report:", response.status_code)
            return False
        result = response.json()
        print("Backend report:", "saved" if result.get("persisted") else "memory only")
        return True
    except Exception as exc:
        print("Backend upload error:", exc)
        return False
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
