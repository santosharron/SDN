SDN Assignment Project

This project contains working code for all four SDN scenarios. Everything is written in Python except the shell based Open vSwitch commands in Scenario 3 and the ONOS CLI commands in Scenario 4. The only Python dependency is the requests library, which you install with pip install requests.

How to run everything

You need a Linux environment with Mininet, Open vSwitch, RYU and ONOS. The easiest option is the official Mininet VM running in VirtualBox or VMware, or an Ubuntu machine where you install mininet, openvswitch and Ryu. Windows cannot run Mininet natively, so run these inside the VM. Scenario 1 also runs anywhere because it is pure Python and it ships with a mock controller for demonstration.

Scenario 1, the automated network policy engine

The file scenario1_policy_engine/policy_engine.py talks to the ONOS Northbound REST API. It fetches all connected switch device IDs with a GET request to /onos/v1/devices, parses the JSON port statistics from /onos/v1/statistics/{device}/ports, computes per port throughput, and when a port exceeds the configured threshold it sends a POST request to /onos/v1/flows/{device} with a flow rule payload that blocks ICMP traffic between the two given IP addresses using an ETH_TYPE 2048 plus IP_PROTO 1 selector and a NOACTION treatment.

To run it against a real ONOS controller, start ONOS, then run python policy_engine.py 3. To run it anywhere without a controller, run python run_demo.py which starts the bundled mock controller and executes the full poll, detect and block cycle. The captured output of a real execution is in outputs/scenario1_output.txt.

Scenario 2, MAC learning and broadcast storm prevention

The file scenario2_mac_learning/mac_learning.py is a RYU controller application. It listens for PacketIn events, parses the Ethernet header fields eth.type, src_mac and dst_mac, keeps a MAC learning table that maps each source MAC to its ingress port, floods packets whose destination MAC is unknown, and installs reactive FlowMod rules once both ends are learned. When the destination is learned it also installs a high priority drop FlowMod for subsequent redundant broadcast frames from that source, which stops broadcast storms caused by topology loops.

Run it with ryu-manager mac_learning.py in one terminal and sudo python loop_topology.py in another. The loop_topology.py file builds two switches connected by two parallel links, which creates the loop. Test with h1 ping -c 3 h2 from the Mininet prompt. A sample of the expected controller log is in outputs/scenario2_output.txt.

Scenario 3, two isolated slices with QoS queues

The file scenario3_qos_slicing/setup_qos.sh contains the raw ovs-vsctl and ovs-ofctl commands. It creates a linux-htb QoS table on the egress port with Queue 1 at a 50 Mbps minimum and 200 Mbps maximum rate for Slice A and Queue 2 at a 10 Mbps minimum and 30 Mbps maximum rate for Slice B, then writes flow rules that match VLAN tag 100 or IP DSCP 46 and send that traffic to Queue 1, and VLAN tag 200 or IP DSCP 34 and send that traffic to Queue 2.

The file scenario3_qos_slicing/slicing_topology.py does the same thing automatically from inside Mininet. Run it with sudo python slicing_topology.py. Verify with ovs-vsctl list queue and ovs-ofctl dump-flows s1. A sample verification output is in outputs/scenario3_output.txt.

Scenario 4, ONOS intent based rerouting

The file scenario4_onos_intents/intent_manager.py creates a point to point intent between H1 with MAC 00:00:00:00:00:01 and H2 with MAC 00:00:00:00:00:02 with a 100 Mbps BandwidthConstraint, polls the REST API until the intent state is INSTALLED, and helps you observe the recompilation after a link failure. The same payload is in intent_payload.json and the equivalent curl and ONOS CLI commands are in onos_commands.txt.

Run python intent_manager.py create to create and verify the intent. Then simulate a link failure on the active path from the Mininet prompt with sh ifconfig s1-eth2 down and watch the state with python intent_manager.py status or the ONOS CLI command intents. ONOS moves the intent through RECOMPILING and INSTALLING back to INSTALLED on the alternate path, or to FAILED if no alternate path exists. Restore the link with sh ifconfig s1-eth2 up. A sample output is in outputs/scenario4_output.txt.

Files

scenario1_policy_engine/policy_engine.py, mock_controller.py, run_demo.py
scenario2_mac_learning/mac_learning.py, loop_topology.py
scenario3_qos_slicing/setup_qos.sh, slicing_topology.py
scenario4_onos_intents/intent_manager.py, intent_payload.json, onos_commands.txt
outputs/scenario1_output.txt and the sample outputs for the other scenarios
