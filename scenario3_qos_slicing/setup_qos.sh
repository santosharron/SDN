#!/bin/bash
# Scenario 3: Two isolated slices on one shared Open vSwitch topology.
# Slice A is high bandwidth streaming video traffic.
# Slice B is low latency restricted bandwidth control signaling.
#
# Run this script on a machine with Open vSwitch installed, for example
# inside the Mininet VM. It configures QoS queues on the switch egress
# ports and writes flow rules that steer each slice into its own queue.

set -e

BRIDGE=s1

# --- Step 1: create queues on the egress port of the bridge -------------
# Queue 1 for Slice A: minimum rate 50 Mbps, maximum rate 200 Mbps.
# Queue 2 for Slice B: minimum rate 10 Mbps, maximum rate 30 Mbps.
# Rates are expressed in bits per second.

ovs-vsctl -- \
  --id=@qA create queue other-config:min-rate=50000000 other-config:max-rate=200000000 \
  --id=@qB create queue other-config:min-rate=10000000 other-config:max-rate=30000000 \
  --id=@qos create qos type=linux-htb other-config:max-rate=1000000000 \
      queues:1=@qA queues:2=@qB \
  -- set port ${BRIDGE}-eth3 qos=@qos

# --- Step 2: flow rules that steer traffic into the queues --------------

# Slice A: video traffic carries VLAN tag 100 or IP DSCP 46 (EF).
ovs-ofctl add-flow ${BRIDGE} "priority=200,dl_vlan=100,actions=set_queue:1,NORMAL"
ovs-ofctl add-flow ${BRIDGE} "priority=200,ip,ip_dscp=46,actions=set_queue:1,NORMAL"

# Slice B: control signaling carries VLAN tag 200 or IP DSCP 34 (AF41).
ovs-ofctl add-flow ${BRIDGE} "priority=200,dl_vlan=200,actions=set_queue:2,NORMAL"
ovs-ofctl add-flow ${BRIDGE} "priority=200,ip,ip_dscp=34,actions=set_queue:2,NORMAL"

# Default traffic uses the normal switching path.
ovs-ofctl add-flow ${BRIDGE} "priority=0,actions=NORMAL"

# --- Step 3: verify ------------------------------------------------------
echo "=== QoS configuration on ${BRIDGE}-eth3 ==="
ovs-vsctl list port ${BRIDGE}-eth3
ovs-vsctl list qos
ovs-vsctl list queue

echo "=== Flow table ==="
ovs-ofctl dump-flows ${BRIDGE}
