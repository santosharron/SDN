"""
Mock SDN Controller Northbound REST API.

Implements the same endpoints as an ONOS controller so that the policy
engine can be executed and demonstrated without a full controller
installation. Port counters grow on every poll so that the traffic
threshold is eventually crossed and the block flow rule is triggered.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEVICES = [
    {"id": "of:0000000000000001", "type": "SWITCH", "available": True},
    {"id": "of:0000000000000002", "type": "SWITCH", "available": True},
]

counters = {}
lock = threading.Lock()
FLOWS = []
BYTES_PER_POLL = 120_000_000


class MockControllerHandler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/onos/v1/devices":
            self._send(200, {"devices": DEVICES})
        elif self.path.startswith("/onos/v1/statistics/") and self.path.endswith("/ports"):
            device_id = self.path.split("/")[4]
            with lock:
                stats = counters.setdefault(device_id, {"rx": 0, "tx": 0})
                stats["rx"] += BYTES_PER_POLL
                stats["tx"] += BYTES_PER_POLL // 2
            self._send(200, {"statistics": [{
                "device": device_id,
                "ports": [
                    {"port": 1, "bytesReceived": stats["rx"], "bytesSent": stats["tx"]},
                    {"port": 2, "bytesReceived": stats["tx"], "bytesSent": stats["rx"]},
                ],
            }]})
        elif self.path.startswith("/onos/v1/flows"):
            self._send(200, {"flows": FLOWS})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path.startswith("/onos/v1/flows/"):
            device_id = self.path.rsplit("/", 1)[1]
            for flow in payload.get("flows", []):
                flow["deviceId"] = device_id
                FLOWS.append(flow)
            self._send(201, {"result": "flow rules added", "count": len(payload.get("flows", []))})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


def start_mock_controller(port=8181):
    server = ThreadingHTTPServer(("127.0.0.1", port), MockControllerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
