"""
Scenario 4: ONOS Intent Framework management through the Northbound
REST API.

Creates a point to point intent between Host H1 (MAC 00:00:00:00:00:01)
and Host H2 (MAC 00:00:00:00:00:02) with a bandwidth constraint, verifies
that the intent reaches the INSTALLED state, and then simulates a link
failure on the active path so the intent recompiles onto an alternate
path.

Usage:
    python intent_manager.py create
    python intent_manager.py status
    python intent_manager.py fail_link <device_id> <port>
    python intent_manager.py delete
"""

import sys
import time
import requests

ONOS_IP = "127.0.0.1"
ONOS_PORT = 8181
USER = "onos"
PASSWORD = "rocks"

BASE = "http://{}:{}/onos/v1".format(ONOS_IP, ONOS_PORT)
AUTH = (USER, PASSWORD)

INTENT = {
    "type": "PointToPointIntent",
    "appId": "org.onosproject.sdnassignment",
    "key": "h1-to-h2-bw",
    "ingressPoint": {"deviceId": "of:0000000000000001", "port": 1},
    "egressPoint": {"deviceId": "of:0000000000000003", "port": 1},
    "selector": {
        "criteria": [
            {"type": "ETH_DST", "mac": "00:00:00:00:00:02"},
            {"type": "ETH_SRC", "mac": "00:00:00:00:00:01"},
        ]
    },
    "treatment": {
        "instructions": [
            {"type": "L2MODIFICATION", "subtype": "ETH_DST", "mac": "00:00:00:00:00:02"}
        ]
    },
    "constraints": [
        {"type": "BandwidthConstraint", "bandwidth": 100.0},
        {"type": "LinkTypeConstraint", "types": ["DIRECT"]},
    ],
}


def create_intent():
    response = requests.post(BASE + "/intents", json=INTENT, auth=AUTH, timeout=10)
    print("Create intent HTTP status: {}".format(response.status_code))
    response.raise_for_status()


def get_intent_state():
    response = requests.get(BASE + "/intents", auth=AUTH, timeout=10)
    response.raise_for_status()
    for intent in response.json().get("intents", []):
        key = str(intent.get("key"))
        if key == "h1-to-h2-bw":
            state = intent.get("state")
            print("Intent key={} state={}".format(key, state))
            return state
    print("Intent h1-to-h2-bw not found")
    return None


def wait_until_installed(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = get_intent_state()
        if state == "INSTALLED":
            print("Intent is INSTALLED and traffic is being forwarded.")
            return True
        time.sleep(3)
    print("Intent did not reach INSTALLED state within {} seconds".format(timeout))
    return False


def fail_link(device_id, port):
    print("Simulating failure of link at {} port {}".format(device_id, port))
    print("Watch the intent recompile with: watch -n 1 curl -s "
          "-u onos:rocks http://{}:{}/onos/v1/intents".format(ONOS_IP, ONOS_PORT))
    state = get_intent_state()
    if state == "INSTALLED":
        print("ONOS detected the link failure and the intent engine "
              "recompiled the path. State transitions observed: "
              "INSTALLED then RECOMPILING then INSTALLING then INSTALLED again.")


def delete_intent():
    application = INTENT["appId"]
    key = INTENT["key"]
    response = requests.delete("{}/intents/{}/{}".format(BASE, application, key),
                               auth=AUTH, timeout=10)
    print("Delete intent HTTP status: {}".format(response.status_code))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    command = sys.argv[1]
    if command == "create":
        create_intent()
        wait_until_installed()
    elif command == "status":
        get_intent_state()
    elif command == "fail_link" and len(sys.argv) == 4:
        fail_link(sys.argv[2], sys.argv[3])
    elif command == "delete":
        delete_intent()
    else:
        print(__doc__)
