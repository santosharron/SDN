"""
Scenario 3: Mininet script that builds the shared topology and applies
the QoS queue configuration for the two isolated slices.

Slice A is high bandwidth streaming video on VLAN 100 / DSCP 46 routed
to Queue 1 with a 50 Mbps minimum and 200 Mbps maximum rate.
Slice B is low latency control signaling on VLAN 200 / DSCP 34 routed
to Queue 2 with a 10 Mbps minimum and 30 Mbps maximum rate.

Run with: sudo python slicing_topology.py
"""

from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, Controller
from mininet.log import setLogLevel
from mininet.cli import CLI

QOS_CMD = (
    "ovs-vsctl -- "
    "--id=@qA create queue other-config:min-rate=50000000 other-config:max-rate=200000000 "
    "--id=@qB create queue other-config:min-rate=10000000 other-config:max-rate=30000000 "
    "--id=@qos create qos type=linux-htb other-config:max-rate=1000000000 "
    "queues:1=@qA queues:2=@qB "
    "-- set port {port} qos=@qos"
)

FLOW_COMMANDS = [
    "ovs-ofctl add-flow {sw} priority=200,dl_vlan=100,actions=set_queue:1,NORMAL",
    "ovs-ofctl add-flow {sw} priority=200,ip,ip_dscp=46,actions=set_queue:1,NORMAL",
    "ovs-ofctl add-flow {sw} priority=200,dl_vlan=200,actions=set_queue:2,NORMAL",
    "ovs-ofctl add-flow {sw} priority=200,ip,ip_dscp=34,actions=set_queue:2,NORMAL",
    "ovs-ofctl add-flow {sw} priority=0,actions=NORMAL",
]


def apply_qos(switch):
    egress_port = "{}-eth3".format(switch.name)
    switch.cmd(QOS_CMD.format(port=egress_port))
    for command in FLOW_COMMANDS:
        switch.cmd(command.format(sw=switch.name))


def run():
    setLogLevel("info")
    net = Mininet(controller=Controller, switch=OVSKernelSwitch)

    c0 = net.addController("c0")
    s1 = net.addSwitch("s1")
    hA = net.addHost("hA", ip="10.0.1.1/24")   # Slice A video source
    hB = net.addHost("hB", ip="10.0.2.1/24")   # Slice B control source
    hD = net.addHost("hD", ip="10.0.0.9/24")   # shared destination

    net.addLink(hA, s1)
    net.addLink(hB, s1)
    net.addLink(s1, hD)

    net.start()
    apply_qos(s1)

    print("QoS queues applied on s1-eth3. Slice A uses Queue 1, Slice B uses Queue 2.")
    print("Verify with: ovs-vsctl list queue  and  ovs-ofctl dump-flows s1")
    CLI(net)
    net.stop()


if __name__ == "__main__":
    run()
