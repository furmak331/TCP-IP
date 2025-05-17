# Add imports
from TCP_IP.physical.device import Device
from TCP_IP.network.ip_address import IPAddress
from TCP_IP.network.packet import Packet # Need to create Packet class
from TCP_IP.datalink.mac_address import MACAddress # Need MACAddress
from TCP_IP.utils.logging_config import setup_logger # Need setup_logger

# Define a simple Interface class (can be more complex later)
class RouterInterface:
    def __init__(self, ip_address_str, subnet_mask_str, link):
        self.ip_address = IPAddress(ip_address_str, subnet_mask_str)
        self.mac_address = MACAddress() # Each interface needs a MAC
        self.link = link # The link connected to this interface
        self.name = f"Int_{self.ip_address.address}" # Simple name based on IP

    def __str__(self):
        return f"{self.name} ({self.ip_address}, MAC: {self.mac_address})"


class Router(Device):
    """Implements a router that forwards packets between networks."""

    def __init__(self, name):
        super().__init__(name)
        # Routing table: {destination_network (IPAddress or str): (output_interface: RouterInterface, next_hop_ip: IPAddress or None)}
        self.routing_table = {}
        self.interfaces = []     # List of RouterInterface objects
        self.logger = setup_logger(f"Router_{name}", f"router_{name}")
        self.arp_table = {} # Router also needs an ARP table

    # Modify add_interface to take IP, mask, and link
    def add_interface(self, ip_address_str, subnet_mask_str, link):
        """Add a network interface with the given IP address, mask, and connected link."""
        new_interface = RouterInterface(ip_address_str, subnet_mask_str, link)
        self.interfaces.append(new_interface)
        # Connect the interface's link to the router (the router is the endpoint)
        link.connect_endpoint(self) # Assuming Link has connect_endpoint method
        self.logger.info(f"Added interface {new_interface} to {self.name}")
        return new_interface

    # Modify remove_interface
    def remove_interface(self, ip_address_str):
        """Remove a network interface with the given IP address."""
        interface_to_remove = None
        for interface in self.interfaces:
            if interface.ip_address.address == ip_address_str:
                interface_to_remove = interface
                break

        if interface_to_remove:
            self.interfaces.remove(interface_to_remove)
            # Disconnect the link
            if interface_to_remove.link:
                 interface_to_remove.link.disconnect_endpoint(self) # Assuming Link has disconnect_endpoint
            self.logger.info(f"Removed interface with IP address {ip_address_str} from {self.name}")
        else:
            self.logger.warning(f"Interface with IP address {ip_address_str} not found on {self.name}")


    # Modify add_route to take destination, output interface, and optional next hop
    def add_route(self, destination_cidr, output_interface_ip_str, next_hop_ip_str=None):
        """Add a route to the routing table. Destination can be network CIDR or host IP."""
        output_interface = None
        for interface in self.interfaces:
            if interface.ip_address.address == output_interface_ip_str:
                output_interface = interface
                break

        if not output_interface:
            self.logger.error(f"Output interface with IP {output_interface_ip_str} not found on {self.name}")
            return False

        try:
            # Use ipaddress to parse destination
            destination_entry = ipaddress.ip_network(destination_cidr, strict=False)
            next_hop_ip = IPAddress(next_hop_ip_str) if next_hop_ip_str else None

            self.routing_table[destination_entry] = (output_interface, next_hop_ip)
            self.logger.info(f"Added route: {destination_cidr} via {output_interface.name}, next hop {next_hop_ip_str or 'direct'}")
            return True
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError) as e:
            self.logger.error(f"Invalid destination CIDR {destination_cidr}: {e}")
            return False


    def remove_route(self, destination_cidr):
        """Remove a route from the routing table."""
        try:
            destination_entry = ipaddress.ip_network(destination_cidr, strict=False)
            if destination_entry in self.routing_table:
                del self.routing_table[destination_entry]
                self.logger.info(f"Removed route to network {destination_cidr} from {self.name}")
                return True
            else:
                self.logger.warning(f"Route to network {destination_cidr} not found on {self.name}")
                return False
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError) as e:
            self.logger.error(f"Invalid destination CIDR {destination_cidr}: {e}")
            return False


    def forward_packet(self, packet, source_interface):
        """Forward a packet to the appropriate next hop based on the routing table."""
        self.logger.info(f"Router {self.name} forwarding packet from {packet.source_ip} to {packet.destination_ip}")

        # Decrement TTL
        packet.ttl -= 1
        if packet.ttl <= 0:
            self.logger.warning(f"Packet from {packet.source_ip} to {packet.destination_ip} TTL expired. Dropping.")
            # TODO: Send ICMP Time Exceeded message back to source
            return False

        # Find the best route using longest mask matching
        best_match = None
        longest_prefix = -1

        try:
            dest_ip_obj = ipaddress.IPv4Address(packet.destination_ip)

            for destination_entry, (output_interface, next_hop_ip) in self.routing_table.items():
                if dest_ip_obj in destination_entry:
                    # Check for longest prefix match
                    if destination_entry.prefixlen > longest_prefix:
                        longest_prefix = destination_entry.prefixlen
                        best_match = (output_interface, next_hop_ip)

        except ipaddress.AddressValueError as e:
             self.logger.error(f"Invalid destination IP in packet {packet.destination_ip}: {e}")
             return False


        if best_match:
            output_interface, next_hop_ip = best_match
            self.logger.info(f"Matched route {output_interface.ip_address.get_network_prefix()} via {output_interface.name}, next hop {next_hop_ip.address if next_hop_ip else 'direct'}")

            # Determine the next hop IP for ARP lookup
            if next_hop_ip:
                # Next hop is a router or specific host
                target_ip_for_arp = next_hop_ip.address
            else:
                # Destination is on a directly connected network
                target_ip_for_arp = packet.destination_ip

            # Perform ARP lookup for the next hop IP
            next_hop_mac = self.arp_lookup(target_ip_for_arp, output_interface)

            if next_hop_mac:
                self.logger.info(f"Next hop IP {target_ip_for_arp} resolved to MAC {next_hop_mac}")
                # Encapsulate the packet in a new frame and send it out the output interface
                # Source MAC is the router's output interface MAC
                # Destination MAC is the next hop's MAC (from ARP)
                frame = Frame(
                    str(output_interface.mac_address),
                    next_hop_mac,
                    packet, # The packet is the data payload of the frame
                    sequence_number=0, # Sequence numbers for Data Link layer
                    frame_type=FrameType.DATA
                )
                self.logger.info(f"Router {self.name} sending frame out {output_interface.name}")
                output_interface.link.transmit(frame, self) # Transmit via the link
                return True
            else:
                self.logger.warning(f"ARP lookup failed for {target_ip_for_arp}. Cannot forward packet.")
                # TODO: Queue packet and send ARP request
                return False

        else:
            self.logger.warning(f"No route found for destination {packet.destination_ip}. Dropping packet.")
            # TODO: Send ICMP Destination Unreachable message back to source
            return False

    # Need to override receive_message to handle incoming frames on interfaces
    def receive_message(self, frame, source_device):
        """Router receives a frame on one of its interfaces."""
        self.logger.info(f"Router {self.name} received frame on a connected link.")

        # Find which interface received the frame
        receiving_interface = None
        for interface in self.interfaces:
            if source_device in [interface.link.endpoint1, interface.link.endpoint2]:
                 receiving_interface = interface
                 break

        if not receiving_interface:
             self.logger.warning(f"Received frame from unknown source device {source_device.name}. Dropping.")
             return

        self.logger.info(f"Received frame on interface {receiving_interface.name}")

        # Process ARP frames first
        if frame.frame_type == FrameType.ARP_REQUEST: # Need ARP frame types
             self.handle_arp_request(frame, receiving_interface)
             return
        elif frame.frame_type == FrameType.ARP_REPLY: # Need ARP frame types
             self.handle_arp_reply(frame, receiving_interface)
             return

        # Process data frames (expecting a Packet inside)
        if frame.frame_type == FrameType.DATA and frame.is_valid():
            # Assuming the frame data is a Packet object
            if isinstance(frame.data, Packet):
                packet = frame.data
                self.process_packet(packet, receiving_interface) # Pass packet to Network Layer processing
            else:
                self.logger.warning(f"Received data frame with non-packet data on {receiving_interface.name}. Dropping.")
        else:
            self.logger.warning(f"Received invalid or non-data frame on {receiving_interface.name}. Dropping.")


    # Placeholder for ARP lookup (will be implemented with ARP protocol)
    def arp_lookup(self, target_ip_str, source_interface):
        """Lookup MAC address for target_ip_str in ARP table. If not found, initiate ARP request."""
        if target_ip_str in self.arp_table:
            self.logger.debug(f"ARP hit for {target_ip_str}: {self.arp_table[target_ip_str]}")
            return self.arp_table[target_ip_str]
        else:
            self.logger.info(f"ARP miss for {target_ip_str}. Initiating ARP request on {source_interface.name}")
            self.send_arp_request(target_ip_str, source_interface) # Need to implement send_arp_request
            # In a real simulator, you'd queue the packet and wait for a reply.
            # For now, return None, the forwarding logic handles the drop/queue.
            return None

    # Placeholder for ARP request handling
    def handle_arp_request(self, frame, receiving_interface):
        """Handle incoming ARP request."""
        # Extract target IP from ARP request data (need ARP frame format)
        # If target IP is one of this router's interface IPs, send ARP reply
        self.logger.info(f"Received ARP request on {receiving_interface.name}")
        # TODO: Implement ARP request processing and reply sending

    # Placeholder for ARP reply handling
    def handle_arp_reply(self, frame, receiving_interface):
        """Handle incoming ARP reply."""
        # Extract sender IP and MAC from ARP reply data (need ARP frame format)
        # Add/update ARP table entry
        self.logger.info(f"Received ARP reply on {receiving_interface.name}")
        # TODO: Implement ARP reply processing and update ARP table

    # Placeholder for sending ARP request
    def send_arp_request(self, target_ip_str, source_interface):
        """Send an ARP request for target_ip_str out of source_interface."""
        self.logger.info(f"Sending ARP request for {target_ip_str} out of {source_interface.name}")
        # TODO: Create and send ARP request frame (broadcast MAC, ARP frame type)

    def __str__(self):
        return f"Router({self.name}, MAC={self.mac_address})"
