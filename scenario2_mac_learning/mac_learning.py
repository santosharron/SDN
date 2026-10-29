"""
Scenario 2: MAC Learning Controller Application with Broadcast Storm
Prevention.

This is a RYU controller application. It listens for PacketIn events,
parses the Ethernet header, maintains a MAC learning table that maps
source MAC addresses to switch ingress ports, floods packets whose
destination MAC is unknown, and installs reactive FlowMod rules so that
once both ends of a conversation are learned, subsequent redundant
broadcast frames from the source are dropped instead of flooded again.

Run with: ryu-manager mac_learning.py
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet


class MacLearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MacLearningSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(datapath.ofproto.OFPC_CONTROLLER,
                                          datapath.ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, idle_timeout=30):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                idle_timeout=idle_timeout, match=match,
                                instructions=inst)
        datapath.send_msg(mod)

    def add_drop_flow(self, datapath, src_mac, dst_mac):
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(eth_src=src_mac, eth_dst=dst_mac)
        self.add_flow(datapath, 100, match, [])

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]

        parsed = packet.Packet(msg.data)
        eth = parsed.get_protocol(ethernet.ethernet)
        if eth is None:
            return

        eth_type = eth.ethertype
        src_mac = eth.src
        dst_mac = eth.dst
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("PacketIn dpid=%s eth.type=0x%04x src=%s dst=%s in_port=%s",
                         dpid, eth_type, src_mac, dst_mac, in_port)

        learned_port = self.mac_to_port[dpid].get(src_mac)
        if learned_port != in_port:
            self.mac_to_port[dpid][src_mac] = in_port
            self.logger.info("Learned src %s on dpid %s port %s", src_mac, dpid, in_port)

        out_port = self.mac_to_port[dpid].get(dst_mac)

        if dst_mac.lower() == "ff:ff:ff:ff:ff:ff" or out_port is None:
            out_port = ofproto.OFPP_FLOOD
            actions = [parser.OFPActionOutput(out_port)]
            self.logger.info("Destination %s unknown, flooding", dst_mac)
        else:
            actions = [parser.OFPActionOutput(out_port)]
            match = parser.OFPMatch(eth_dst=dst_mac, eth_src=src_mac)
            self.add_flow(datapath, 10, match, actions)
            self.logger.info("Destination %s known on port %s, installing reactive FlowMod",
                             dst_mac, out_port)
            self.add_drop_flow(datapath, src_mac, "ff:ff:ff:ff:ff:ff")
            self.logger.info("Installed drop FlowMod for redundant broadcast frames from %s",
                             src_mac)

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=msg.data)
        datapath.send_msg(out)
