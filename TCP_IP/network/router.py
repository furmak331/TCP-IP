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

    # New method to process received packets (Network Layer)
    def process_packet(self, packet, source_interface):
        """Process a received network layer packet."""
        self.logger.info(f"Router {self.name} received packet from {packet.source_ip} to {packet.destination_ip} on {source_interface.name}")

        # Check if the packet is for this router (any of its interface IPs or multicast/broadcast)
        is_for_me = False
        if self.ip_address and packet.destination_ip == self.ip_address.address:
             is_for_me = True
        else:
             # Check if destination is one of the router's interface IPs
             for interface in self.interfaces:
                 if packet.destination_ip == interface.ip_address.address:
                     is_for_me = True
                     break
             # Check for multicast/broadcast relevant to the router (e.g., RIP multicast)
             # This is a simplification; proper multicast handling is complex.
             # For RIPv2, check for 224.0.0.9
             if packet.destination_ip == "224.0.0.9":
                 is_for_me = True


        if is_for_me:
            self.logger.info(f"Packet for me! Protocol: {packet.protocol}, Data: {packet.data}")
            # Pass data up to the next layer (Transport Layer - not implemented yet)
            # For now, handle specific protocols like RIP
            if packet.protocol == 17: # Assuming 17 is UDP, and this is a RIP packet
                 self.handle_rip_packet(packet, source_interface)
            else:
                 # Handle other protocols or pass up
                 self.received_messages.append((packet.data, packet.source_ip)) # Store for now

        else:
            self.logger.info(f"Packet not for me, needs routing.")
            # Forward the packet
            self.forward_packet(packet, source_interface) # Router's forwarding logic

    # Placeholder for handling RIP packets
    def handle_rip_packet(self, packet, receiving_interface):
        """Handle incoming RIP packet (UDP payload)."""
        if not self.rip_enabled:
            self.logger.debug(f"Received RIP packet on {self.name}, but RIP is disabled.")
            return

        # Assuming packet.data is the RIP message structure (e.g., a dictionary)
        rip_message = packet.data
        sender_ip = packet.source_ip

        if not isinstance(rip_message, dict) or 'command' not in rip_message or 'entries' not in rip_message:
            self.logger.warning(f"Received malformed RIP message from {sender_ip}")
            return

        command = rip_message['command']
        entries = rip_message['entries']

        self.logger.info(f"Received RIP {command} from {sender_ip} on {receiving_interface.name} with {len(entries)} entries.")

        if command == "request":
            # Send a RIP response back to the sender (unicast)
            self.logger.info(f"Responding to RIP request from {sender_ip}")
            self._send_rip_response_to_neighbor(sender_ip, receiving_interface)

        elif command == "response":
            # Process the received RIP routes
            self._process_rip_response(sender_ip, receiving_interface, entries)

        else:
            self.logger.warning(f"Received unknown RIP command '{command}' from {sender_ip}")


    # Helper to send a unicast RIP response to a specific neighbor
    def _send_rip_response_to_neighbor(self, neighbor_ip_str, output_interface):
        """Send a RIP response containing our routes to a specific neighbor."""
        rip_response_data = []
        for dest_network, (output_int, next_hop, metric, source) in self.routing_table.items():
            # Implement Split Horizon: Don't advertise routes learned via this interface back out this interface
            # Or implement Poisoned Reverse: Advertise with metric 16
            if source == "RIP" and output_int == output_interface:
                # Simple Split Horizon: Don't include this route
                continue
            else:
                # Add route to the update (increment metric by 1 for neighbors)
                # Ensure metric doesn't exceed infinity
                advertised_metric = min(metric + 1, self.RIP_METRIC_INFINITY)
                rip_response_data.append({"network": str(dest_network), "metric": advertised_metric})

        if rip_response_data:
            rip_packet_data = {"command": "response", "entries": rip_response_data}

            # Send as an IP packet (unicast)
            self.send_packet(
                destination_ip_str=neighbor_ip_str,
                data=rip_packet_data,
                protocol=17, # UDP protocol number
                source_interface=output_interface # Need to modify send_packet
            )


    # Helper to process incoming RIP response entries
    def _process_rip_response(self, neighbor_ip_str, receiving_interface, entries):
        """Process RIP route entries received from a neighbor."""
        neighbor_ip = IPAddress(neighbor_ip_str)

        for entry in entries:
            try:
                dest_cidr = entry.get("network")
                metric = entry.get("metric")

                if dest_cidr is None or metric is None:
                    self.logger.warning(f"Malformed RIP entry received from {neighbor_ip_str}: {entry}")
                    continue

                dest_network = ipaddress.ip_network(dest_cidr, strict=False)
                received_metric = int(metric)

                # Ignore routes with metric 16 (unreachable) unless we need to update an existing route to 16
                if received_metric >= self.RIP_METRIC_INFINITY:
                    # If we have a route to this network learned from this neighbor, mark it as unreachable
                    current_route = self.routing_table.get(dest_network)
                    if current_route and current_route[0] == receiving_interface and current_route[3] == "RIP":
                         self.logger.info(f"Received unreachable route for {dest_network} from {neighbor_ip_str}. Marking as unreachable.")
                         self.routing_table[dest_network] = (receiving_interface, neighbor_ip, self.RIP_METRIC_INFINITY, "RIP")
                         self.rip_route_timestamps[dest_network] = time.time() # Update timestamp
                         # TODO: Trigger a poisoned reverse update for this route?

                    continue # Don't add unreachable routes

                # Calculate the metric to reach the destination via this neighbor
                cost_via_neighbor = received_metric + 1

                # Ignore if the cost is already infinity
                if cost_via_neighbor >= self.RIP_METRIC_INFINITY:
                    continue

                # Check if we already have a route to this destination
                current_route = self.routing_table.get(dest_network)

                if current_route:
                    current_metric = current_route[2]
                    current_output_int = current_route[0]
                    current_next_hop = current_route[1]
                    current_source = current_route[3]

                    # If the received route is from the neighbor that is our current next hop for this route,
                    # update the route (even if the metric is the same or worse, unless it's infinity).
                    # This handles updates and potential route poisoning.
                    if current_output_int == receiving_interface and (current_next_hop is None or current_next_hop.address == neighbor_ip_str):
                         if cost_via_neighbor != current_metric or current_source != "RIP":
                             self.logger.info(f"Updating route to {dest_network} via {neighbor_ip_str} (learned from {receiving_interface.name}). Metric: {current_metric} -> {cost_via_neighbor}")
                             self.routing_table[dest_network] = (receiving_interface, neighbor_ip, cost_via_neighbor, "RIP")
                             self.rip_route_timestamps[dest_network] = time.time() # Update timestamp
                             # TODO: Trigger an update?

                    # If the received route offers a better metric
                    elif cost_via_neighbor < current_metric:
                        self.logger.info(f"Found better route to {dest_network} via {neighbor_ip_str} (learned from {receiving_interface.name}). Metric: {current_metric} -> {cost_via_neighbor}")
                        self.routing_table[dest_network] = (receiving_interface, neighbor_ip, cost_via_neighbor, "RIP")
                        self.rip_route_timestamps[dest_network] = time.time() # Update timestamp
                        # TODO: Trigger an update?

                    # If the received route has the same metric but is from a different neighbor (potential tie-breaking or equal-cost load balancing - optional)
                    # elif cost_via_neighbor == current_metric and current_output_int != receiving_interface:
                    #     self.logger.debug(f"Found equal cost route to {dest_network} via {neighbor_ip_str}. Current via {current_output_int.name}")
                    #     # You could add this as an alternative path for load balancing if supported

                else:
                    # No existing route, add the new RIP route
                    self.logger.info(f"Learned new route to {dest_network} via {neighbor_ip_str} (learned from {receiving_interface.name}). Metric: {cost_via_neighbor}")
                    self.routing_table[dest_network] = (receiving_interface, neighbor_ip, cost_via_neighbor, "RIP")
                    self.rip_route_timestamps[dest_network] = time.time() # Record timestamp
                    # TODO: Trigger an update?


            except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError) as e:
                self.logger.warning(f"Error processing RIP entry from {neighbor_ip_str}: {entry} - {e}")
