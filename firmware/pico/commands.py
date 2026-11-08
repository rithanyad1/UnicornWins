"""Poll backend commands and retry acknowledgments without executing twice."""

try:
    import requests
except ImportError:
    import urequests as requests


class CommandClient:
    def __init__(self, backend_url, token, timeout=2):
        self.base = backend_url.rstrip("/")
        self.headers = {"X-Device-Token": token}
        self.timeout = timeout
        self.pending_ack = None

    def poll(self, wifi, execute):
        if not wifi.isconnected():
            return
        response = None
        try:
            # A failed ACK is retried before fetching or executing another command.
            if self.pending_ack is None:
                response = requests.get(
                    self.base + "/api/v1/devices/sentinel-pico/commands/next",
                    headers=self.headers, timeout=self.timeout,
                )
                if response.status_code != 200:
                    print("Backend command poll:", response.status_code)
                    return
                command = response.json().get("command")
                response.close()
                response = None
                if command is None:
                    return
                try:
                    state = execute(command)
                    ack = {"status": "EXECUTED", "reported_state": state}
                except Exception as exc:
                    ack = {"status": "FAILED", "reported_state": {},
                           "failure_reason": str(exc)[:500]}
                self.pending_ack = (command["id"], ack)

            command_id, ack = self.pending_ack
            response = requests.post(
                self.base + "/api/v1/commands/" + command_id + "/ack",
                headers=self.headers, json=ack, timeout=self.timeout,
            )
            print("Backend command ack:", response.status_code)
            # Unknown/expired commands cannot be retried after a backend restart.
            if response.status_code in (200, 404, 409):
                self.pending_ack = None
        except Exception as exc:
            print("Backend command error:", exc)
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
