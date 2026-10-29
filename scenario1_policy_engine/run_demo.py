"""
Runs the policy engine against the bundled mock controller so the whole
Scenario 1 flow can be demonstrated on any machine with Python and the
requests library installed.
"""

import sys
import mock_controller
from policy_engine import NetworkPolicyEngine


def main():
    server = mock_controller.start_mock_controller(8181)
    print("Mock SDN controller listening on http://127.0.0.1:8181")
    host_ports = {1: ("10.0.0.1", "10.0.0.2"), 2: ("10.0.0.2", "10.0.0.1")}
    engine = NetworkPolicyEngine(
        controller_ip="127.0.0.1",
        controller_port=8181,
        threshold_mbps=800.0,
        poll_interval=1,
    )
    try:
        engine.run(host_ports, iterations=3)
    finally:
        server.shutdown()
    print("Final flow rules held by the controller:")
    import json
    print(json.dumps(mock_controller.FLOWS, indent=2))


if __name__ == "__main__":
    sys.exit(main())
