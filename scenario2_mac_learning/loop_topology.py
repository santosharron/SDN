"""
Scenario 2 test topology: a looped Mininet topology.

Two switches are connected by two parallel links which creates a
topology loop. Without the MAC learning and broadcast drop logic in
mac_learning.py, broadcast frames circulate forever and cause a
broadcast storm. Run this together with the RYU controller:

    ryu-manager mac_learning.py
    python loop_topology.py

Then inside Mininet test with:
    h1 ping -c 3 h2
    h1 ping -c 3 h3
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.log import setLogLevel


class LoopTopo(Topo):
    def build(self):
        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")
        h1 = self.addHost("h1", mac="00:00:00:00:00:01", ip="10.0.0.1/24")
        h2 = self.addHost("h2", mac="00:00:00:00:00:02", ip="10.0.0.2/24")
        h3 = self.addHost("h3", mac="00:00:00:00:00:03", ip="10.0.0.3/24")
        self.addLink(h1, s1)
        self.addLink(h2, s2)
        self.addLink(h3, s2)
        self.addLink(s1, s2)
        self.addLink(s1, s2)


def run():
    setLogLevel("info")
    topo = LoopTopo()
    net = Mininet(topo=topo, switch=OVSKernelSwitch,
                  controller=RemoteController("c0", ip="127.0.0.1", port=6633))
    net.start()
    print("Looped topology is up. Broadcast storm test: h1 ping -c 3 h2")
    net.staticArp()
    net.cli()
    net.stop()


if __name__ == "__main__":
    run()
