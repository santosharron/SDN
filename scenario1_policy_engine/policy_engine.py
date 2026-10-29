"""
Scenario 1: Automated Network Policy Engine for an SDN Controller.

This application talks to the Northbound REST API of an ONOS style SDN
controller. It continuously polls the controller for connected switch
devices, reads port statistics, computes per port throughput, and when a
port crosses the configured traffic threshold it injects a flow rule that
blocks ICMP traffic between the two hosts that are generating the load.

The same logic runs against a real controller or against the bundled
mock_controller.py for demonstration and testing.
"""

import time
import sys
import requests


class NetworkPolicyEngine:
    def __init__(self, controller_ip="127.0.0.1", controller_port=8181,
                 username="onos", password="rocks",
                 threshold_mbps=800.0, poll_interval=5, block_priority=40000):
        self.base_url = "http://{}:{}/onos/v1".format(controller_ip, controller_port)
        self.auth = (username, password)
        self.threshold_mbps = threshold_mbps
        self.poll_interval = poll_interval
        self.block_priority = block_priority
        self.session = requests.Session()
        self.session.auth = self.auth
        self._previous_counters = {}
        self.blocked_pairs = set()

    def get_device_ids(self):
        response = self.session.get(self.base_url + "/devices", timeout=10)
        response.raise_for_status()
        data = response.json()
        device_ids = [device["id"] for device in data.get("devices", [])]
        return device_ids

    def get_port_statistics(self, device_id):
        response = self.session.get(
            self.base_url + "/statistics/{}/ports".format(device_id), timeout=10)
        response.raise_for_status()
        data = response.json()
        port_stats = []
        for entry in data.get("statistics", []):
            for stat in entry.get("ports", []):
                port_stats.append({
                    "device": entry.get("device", device_id),
                    "port": stat.get("port"),
                    "bytes_received": stat.get("bytesReceived", 0),
                    "bytes_sent": stat.get("bytesSent", 0),
                })
        return port_stats

    def compute_throughput_mbps(self, device_id, port, stats, interval):
        key = (device_id, port)
        current_total = stats["bytes_received"] + stats["bytes_sent"]
        previous_total = self._previous_counters.get(key, current_total)
        delta_bytes = max(0, current_total - previous_total)
        self._previous_counters[key] = current_total
        if interval <= 0:
            return 0.0
        return (delta_bytes * 8.0) / (interval * 1_000_000.0)

    def build_icmp_block_flow(self, device_id, src_ip, dst_ip):
        flow = {
            "priority": self.block_priority,
            "timeout": 0,
            "isPermanent": True,
            "deviceId": device_id,
            "treatment": {
                "instructions": [{"type": "NOACTION"}]
            },
            "selector": {
                "criteria": [
                    {"type": "ETH_TYPE", "ethType": 2048},
                    {"type": "IP_PROTO", "protocol": 1},
                    {"type": "IPV4_SRC", "ip": src_ip + "/32"},
                    {"type": "IPV4_DST", "ip": dst_ip + "/32"},
                ]
            }
        }
        return {"flows": [flow]}

    def block_icmp_between(self, device_id, src_ip, dst_ip):
        url = self.base_url + "/flows/" + device_id
        payload = self.build_icmp_block_flow(device_id, src_ip, dst_ip)
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        pair = (src_ip, dst_ip)
        self.blocked_pairs.add(pair)
        return response

    def check_and_enforce(self, host_map):
        device_ids = self.get_device_ids()
        print("Connected switch devices: {}".format(device_ids))
        violations = []
        for device_id in device_ids:
            port_stats = self.get_port_statistics(device_id)
            for stats in port_stats:
                mbps = self.compute_throughput_mbps(
                    device_id, stats["port"], stats, self.poll_interval)
                print("  device {} port {} throughput {:.2f} Mbps".format(
                    device_id, stats["port"], mbps))
                if mbps > self.threshold_mbps:
                    violations.append((device_id, stats["port"], mbps))
        for device_id, port, mbps in violations:
            src_ip, dst_ip = host_map.get(port, ("10.0.0.1", "10.0.0.2"))
            if (src_ip, dst_ip) in self.blocked_pairs:
                print("  ICMP already blocked between {} and {}".format(src_ip, dst_ip))
                continue
            print("  THRESHOLD EXCEEDED on {} port {} at {:.2f} Mbps".format(
                device_id, port, mbps))
            response = self.block_icmp_between(device_id, src_ip, dst_ip)
            print("  Injected ICMP block flow rule, HTTP status {}".format(
                response.status_code))
        return violations

    def run(self, host_map, iterations=None):
        iteration = 0
        while iterations is None or iteration < iterations:
            iteration += 1
            print("Poll {} at {}".format(iteration, time.strftime("%H:%M:%S")))
            try:
                self.check_and_enforce(host_map)
            except requests.RequestException as exc:
                print("Controller communication failed: {}".format(exc))
            if iterations is not None and iteration >= iterations:
                break
            time.sleep(self.poll_interval)


if __name__ == "__main__":
    host_ports = {1: ("10.0.0.1", "10.0.0.2"), 2: ("10.0.0.2", "10.0.0.1")}
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    engine = NetworkPolicyEngine(
        controller_ip="127.0.0.1",
        controller_port=8181,
        threshold_mbps=800.0,
        poll_interval=2,
    )
    engine.run(host_ports, iterations=iterations)
