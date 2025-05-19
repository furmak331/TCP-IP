"""
TCP/IP Network Simulator
A modular simulator focusing on the Physical, Data Link, and Network Layers.
"""

import uuid
import random
import time
import logging
import os
import threading
from enum import Enum
import ipaddress
from typing import Dict, List, Optional, Tuple, Set

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Setup logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Constants
MAX_FRAME_SIZE = 1024
TRANSMISSION_DELAY = 0.01
BIT_ERROR_RATE = 0.05
CSMA_CD_MAX_ATTEMPTS = 16
CSMA_CD_SLOT_TIME = 0.02
MEDIUM_BUSY_PROBABILITY = 0.3
MEDIUM_BUSY_DURATION = 0.1
ERROR_INJECTION_RATE = 0.05
BUSY_TIME_RANGE = (0.05, 0.2)
DEFAULT_TTL = 64
IP_HEADER_SIZE = 20
MAX_PACKETS = 20
PACKET_LOSS_RATE = 0.05

class IPAddress:
    """Represents an IPv4 address with subnet mask"""
    
    def __init__(self, address: str, subnet_mask: str = "255.255.255.0"):
        self.network = ipaddress.IPv4Network(f"{address}/{subnet_mask}", strict=False)
        self.ip = ipaddress.IPv4Address(address)
        self.mask = ipaddress.IPv4Address(subnet_mask)
    
    @property
    def address(self) -> str:
        return str(self.ip)
    
    @property
    def subnet(self) -> str:
        return str(self.mask)
    
    @property
    def network_address(self) -> str:
        return str(self.network.network_address)
    
    def is_in_same_network(self, other: 'IPAddress') -> bool:
        """Check if another IP address is in the same network"""
        return self.network == other.network
    
    def __str__(self) -> str:
        return f"{self.address}/{self.network.prefixlen}"

class RoutingTableEntry:
    """Represents an entry in a routing table"""
    
    def __init__(self, destination: str, next_hop: str, subnet_mask: str,
                 interface: str, metric: int = 1):
        self.destination = ipaddress.IPv4Network(f"{destination}/{subnet_mask}", strict=False)
        self.next_hop = next_hop
        self.subnet_mask = subnet_mask
        self.interface = interface
        self.metric = metric
        self.timestamp = time.time()
    
    def __str__(self) -> str:
        return f"{self.destination} via {self.next_hop} on {self.interface} metric {self.metric}"

class RoutingTable:
    """Implements a routing table with longest prefix match"""
    
    def __init__(self):
        self.routes: List[RoutingTableEntry] = []
        self.logger = logging.getLogger("RoutingTable")
    
    def add_route(self, destination: str, next_hop: str, subnet_mask: str,
                 interface: str, metric: int = 1) -> None:
        """Add a route to the routing table"""
        entry = RoutingTableEntry(destination, next_hop, subnet_mask, interface, metric)
        self.routes.append(entry)
        self.logger.info(f"Added route: {entry}")
    
    def remove_route(self, destination: str, subnet_mask: str) -> bool:
        """Remove a route from the routing table"""
        network = ipaddress.IPv4Network(f"{destination}/{subnet_mask}", strict=False)
        for route in self.routes[:]:
            if route.destination == network:
                self.routes.remove(route)
                self.logger.info(f"Removed route: {route}")
                return True
        return False
    
    def lookup(self, destination: str) -> Optional[RoutingTableEntry]:
        """Find the best route for a destination using longest prefix match"""
        dest_ip = ipaddress.IPv4Address(destination)
        best_match = None
        best_prefix_len = -1
        
        for route in self.routes:
            if dest_ip in route.destination:
                prefix_len = route.destination.prefixlen
                if prefix_len > best_prefix_len:
                    best_match = route
                    best_prefix_len = prefix_len
        
        if best_match:
            self.logger.info(f"Route lookup for {destination}: found {best_match}")
        else:
            self.logger.warning(f"No route found for {destination}")
        
        return best_match

class Frame:
    def __init__(self, dest_mac: str, src_mac: str, data: str, type: int = 0x0800, sequence_number: int = 0):
        self.destination_mac = dest_mac
        self.source_mac = src_mac
        self.type = type
        self.data = data
        self.sequence_number = sequence_number
        self.ack_number = 0
        self.fcs = self._calculate_fcs()
    
    def _calculate_fcs(self) -> int:
        fcs = 0
        for c in self.destination_mac + self.source_mac + str(self.type) + self.data:
            fcs = (fcs + ord(c)) & 0xFFFFFFFF
        return fcs
    
    def is_valid(self) -> bool:
        return self._calculate_fcs() == self.fcs
    
    def __str__(self) -> str:
        return f"Frame[{self.sequence_number}] {self.source_mac}->{self.destination_mac} Type:0x{self.type:04x} Data:{self.data[:20]}"

class IPPacket:
    def __init__(self, src_ip: str, dest_ip: str, data: str, protocol: int = 6):
        self.version = 4
        self.header_length = 5
        self.total_length = len(data) + 20
        self.src_ip = src_ip
        self.dest_ip = dest_ip
        self.protocol = protocol
        self.ttl = 64
        self.data = data
        self.id = random.randint(0, 65535)
        self.flags = 0
        self.checksum = self._calculate_checksum()
        self.route_trace = []  # List to store route information
    
    def add_to_route(self, device_name: str, device_type: str, interface: str = None):
        """Add a device to the route trace"""
        hop = {
            'device': device_name,
            'type': device_type,
            'interface': interface,
            'timestamp': time.time()
        }
        self.route_trace.append(hop)
    
    def get_route_summary(self) -> str:
        """Get a formatted summary of the packet's route"""
        if not self.route_trace:
            return "No route information available"
        
        summary = f"\nRoute from {self.src_ip} to {self.dest_ip}:\n"
        for i, hop in enumerate(self.route_trace, 1):
            interface_info = f" via {hop['interface']}" if hop['interface'] else ""
            summary += f"{i}. {hop['type']}: {hop['device']}{interface_info}\n"
        return summary
    
    def _calculate_checksum(self) -> int:
        sum = 0
        header = (
            str(self.version) +
            str(self.header_length) +
            str(self.total_length) +
            str(self.id) +
            str(self.flags) +
            str(self.ttl) +
            str(self.protocol) +
            self.src_ip +
            self.dest_ip
        )
        for c in header:
            sum = (sum + ord(c)) & 0xFFFF
        return sum ^ 0xFFFF
    
    def is_valid(self) -> bool:
        return self._calculate_checksum() == self.checksum and self.ttl > 0
    
    def decrement_ttl(self) -> bool:
        self.ttl -= 1
        return self.ttl > 0
    
    def __str__(self) -> str:
        return f"IPv4[{self.id}] {self.src_ip}->{self.dest_ip} TTL:{self.ttl} Proto:{self.protocol} Data:{self.data[:20]}"

class TCPSegment:
    def __init__(self, src_port: int, dest_port: int, data: str):
        self.src_port = src_port
        self.dest_port = dest_port
        self.sequence_number = random.randint(0, 65535)
        self.ack_number = 0
        self.data_offset = 5
        self.flags = 0  # URG=32, ACK=16, PSH=8, RST=4, SYN=2, FIN=1
        self.window = 1024
        self.data = data
        self.checksum = self._calculate_checksum()
    
    def set_ack(self, ack: bool = True):
        if ack:
            self.flags |= 16
        else:
            self.flags &= ~16
    
    def set_syn(self, syn: bool = True):
        if syn:
            self.flags |= 2
        else:
            self.flags &= ~2
    
    def set_fin(self, fin: bool = True):
        if fin:
            self.flags |= 1
        else:
            self.flags &= ~1
    
    def _calculate_checksum(self) -> int:
        sum = 0
        header = (
            str(self.src_port) +
            str(self.dest_port) +
            str(self.sequence_number) +
            str(self.ack_number) +
            str(self.data_offset) +
            str(self.flags) +
            str(self.window)
        )
        for c in header + self.data:
            sum = (sum + ord(c)) & 0xFFFF
        return sum ^ 0xFFFF
    
    def is_valid(self) -> bool:
        return self._calculate_checksum() == self.checksum
    
    def __str__(self) -> str:
        flags = []
        if self.flags & 32: flags.append("URG")
        if self.flags & 16: flags.append("ACK")
        if self.flags & 8: flags.append("PSH")
        if self.flags & 4: flags.append("RST")
        if self.flags & 2: flags.append("SYN")
        if self.flags & 1: flags.append("FIN")
        flag_str = "|".join(flags) if flags else "None"
        
        return f"TCP[SEQ={self.sequence_number} ACK={self.ack_number}] {self.src_port}->{self.dest_port} Flags:{flag_str} Data:{self.data[:20]}"

class NetworkInterface:
    """Represents a network interface with IP configuration"""
    
    def __init__(self, name: str, ip_address: str, subnet_mask: str):
        self.name = name
        self.ip = IPAddress(ip_address, subnet_mask)
        self.enabled = True
        self.mtu = 1500  # Maximum Transmission Unit
        self.logger = logging.getLogger(f"Interface_{name}")
        self.fragment_buffer = {}  # Buffer for reassembling fragments
        self.fragment_timeout = 60  # Timeout for fragment reassembly in seconds
    
    def fragment_packet(self, packet: IPPacket) -> List[IPPacket]:
        """Fragment a packet if it exceeds MTU"""
        data_size = len(packet.data)
        if data_size <= self.mtu - IP_HEADER_SIZE:
            return [packet]
        
        # Calculate maximum data per fragment
        max_data = self.mtu - IP_HEADER_SIZE
        fragments = []
        offset = 0
        
        while offset < data_size:
            # Create fragment
            fragment_data = packet.data[offset:offset + max_data]
            fragment = IPPacket(
                packet.src_ip,
                packet.dest_ip,
                fragment_data,
                packet.protocol,
                packet.ttl
            )
            
            # Set fragmentation flags and offset
            fragment.flags = 1 if offset + max_data < data_size else 0
            fragment.id = packet.id  # Keep same ID for all fragments
            
            fragments.append(fragment)
            offset += max_data
        
        self.logger.info(f"Fragmented packet {packet.id} into {len(fragments)} fragments")
        return fragments
    
    def reassemble_packet(self, fragment: IPPacket) -> Optional[IPPacket]:
        """Reassemble original packet from fragments"""
        packet_key = (fragment.src_ip, fragment.dest_ip, fragment.id)
        current_time = time.time()
        
        # Initialize or update fragment buffer
        if packet_key not in self.fragment_buffer:
            self.fragment_buffer[packet_key] = {
                'fragments': {},
                'timestamp': current_time
            }
        
        # Store fragment
        offset = fragment.id * 8
        self.fragment_buffer[packet_key]['fragments'][offset] = fragment
        self.fragment_buffer[packet_key]['timestamp'] = current_time
        
        # Check if we have all fragments
        fragments = self.fragment_buffer[packet_key]['fragments']
        if not fragment.flags:  # This is the last fragment
            # Calculate total size and check for missing fragments
            total_size = fragment.id * 8 + len(fragment.data)
            current_size = 0
            data = []
            
            # Reconstruct original data
            for offset in sorted(fragments.keys()):
                frag = fragments[offset]
                if current_size != offset:
                    # Gap in fragments
                    return None
                data.append(frag.data)
                current_size += len(frag.data)
            
            if current_size == total_size:
                # All fragments received, reconstruct packet
                reassembled_data = ''.join(data)
                packet = IPPacket(
                    fragment.src_ip,
                    fragment.dest_ip,
                    reassembled_data,
                    fragment.protocol,
                    fragment.ttl
                )
                packet.id = fragment.id
                
                # Clean up fragment buffer
                del self.fragment_buffer[packet_key]
                self.logger.info(f"Reassembled packet {packet.id}")
                return packet
        
        return None
    
    def cleanup_fragments(self):
        """Remove timed out fragments"""
        current_time = time.time()
        for key in list(self.fragment_buffer.keys()):
            if current_time - self.fragment_buffer[key]['timestamp'] > self.fragment_timeout:
                del self.fragment_buffer[key]
                self.logger.warning(f"Removed timed out fragments for packet {key}")
    
    def enable(self) -> None:
        """Enable the interface"""
        self.enabled = True
        self.logger.info(f"Interface {self.name} enabled")
    
    def disable(self) -> None:
        """Disable the interface"""
        self.enabled = False
        self.logger.info(f"Interface {self.name} disabled")
    
    def is_in_network(self, ip_address: str) -> bool:
        """Check if an IP address is in this interface's network"""
        other_ip = IPAddress(ip_address, self.ip.subnet)
        return self.ip.is_in_same_network(other_ip)
    
    def __str__(self) -> str:
        status = "UP" if self.enabled else "DOWN"
        return f"Interface {self.name}: {self.ip} MTU:{self.mtu} Status:{status}"

class MACAddress:
    """Represents a MAC address for network devices"""
    
    def __init__(self, address=None):
        if address:
            self.address = address
        else:
            # Generate a random MAC address if none provided
            self.address = ':'.join(['{:02x}'.format(random.randint(0, 255)) for _ in range(6)])
    
    def __str__(self):
        return self.address
    
    def __eq__(self, other):
        if isinstance(other, MACAddress):
            return self.address == other.address
        elif isinstance(other, str):
            return self.address == other
        return False
    
    def __hash__(self):
        return hash(self.address)


class FrameType(Enum):
    """Enum for different frame types"""
    DATA = 1
    ACK = 2
    NAK = 3


class Device:
    """Base class for all network devices."""
    
    def __init__(self, name):
        self.name = name
        self.mac_address = MACAddress()
        self.ip_address = None  # Will be set when configuring network
        self.connections = []  # List of links connected to this device
        self.received_messages = []  # Messages received by this device
        self.logger = self._setup_logger()
        self.logger.info(f"Device {self.name} created with MAC {self.mac_address}")
        
        # Data Link Layer properties
        self.next_sequence_number = 0
        self.expected_sequence_number = 0
        self.window_size = 4  # Window size for sliding window protocol
        self.timeout = 1.0  # Timeout in seconds for retransmission
        self.unacknowledged_frames = {}  # sequence_number -> (frame, timestamp)
        self.buffer = []  # Buffer for received out-of-order frames
        
        # Network Layer properties
        self.default_gateway = None  # IP address of default gateway
        self.subnet_mask = None  # Subnet mask for the network
    
    def _setup_logger(self):
        """Setup a logger for this device"""
        logger = logging.getLogger(f"{self.name}")
        file_handler = logging.FileHandler(f"logs/{self.name}.log")
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        return logger
    
    def connect(self, link):
        """Connect this device to a link."""
        self.connections.append(link)
        self.logger.info(f"Connected to link {link.name}")
    
    def disconnect(self, link):
        """Disconnect this device from a link."""
        if link in self.connections:
            self.connections.remove(link)
            self.logger.info(f"Disconnected from link {link.name}")
    
    def configure_network(self, ip_address: str, subnet_mask: str, default_gateway: Optional[str] = None):
        """Configure network settings for the device"""
        self.ip_address = IPAddress(ip_address, subnet_mask)
        self.subnet_mask = subnet_mask
        self.default_gateway = default_gateway
        self.logger.info(f"Configured network: IP={ip_address}, Mask={subnet_mask}, Gateway={default_gateway}")
    
    def send_message(self, message, target_mac=None, target_ip=None):
        """Send a message through all connected links."""
        if not self.connections:
            self.logger.error(f"Cannot send message: No connections available")
            return False
        
        if target_ip and not self.ip_address:
            self.logger.error(f"Cannot send IP packet: Device not configured with IP address")
            return False
        
        self.logger.info(f"Sending message: {message}")
        
        if target_ip:
            # Create IP packet
            packet = IPPacket(self.ip_address.address, target_ip, message)
            # Add source to route trace
            packet.add_to_route(self.name, "Device")
            
            # Determine next hop
            next_hop = target_ip
            if not IPAddress(target_ip, self.subnet_mask).is_in_same_network(self.ip_address):
                if not self.default_gateway:
                    self.logger.error(f"Cannot reach {target_ip}: No default gateway configured")
                    return False
                next_hop = self.default_gateway
            
            # Create frame with IP packet as data
            frames = self._create_frames(str(packet), target_mac)
        else:
            # Create regular frames without IP
            frames = self._create_frames(message, target_mac)
        
        # Send using the configured protocol
        if hasattr(self, 'use_go_back_n') and self.use_go_back_n:
            success = self._send_go_back_n(frames)
        else:
            success = self._send_stop_and_wait(frames)
        
        return success
    
    def _create_frames(self, message, target_mac):
        """Split a message into frames with efficient packing to reduce frame count"""
        frames = []
        # If target_mac is None, use broadcast address
        dest_mac = target_mac if target_mac else "FF:FF:FF:FF:FF:FF"
        
        # Use more efficient framing - pack more data per frame
        # Instead of one character per frame, use chunks of 20 characters
        chunk_size = 20
        message_chunks = [message[i:i+chunk_size] for i in range(0, len(message), chunk_size)]
        
        # Create a special first frame with total message size
        size_frame = Frame(
            dest_mac,
            str(self.mac_address), 
            f"__SIZE__{len(message)}",
            type=0x0800,
            sequence_number=self.next_sequence_number
        )
        frames.append(size_frame)
        self.next_sequence_number += 1
        
        # Create a frame for each chunk of the message
        for chunk in message_chunks:
            frame = Frame(
                dest_mac,
                str(self.mac_address),
                chunk,
                type=0x0800,
                sequence_number=self.next_sequence_number
            )
            frames.append(frame)
            self.next_sequence_number += 1
        
        return frames
    
    def _send_stop_and_wait(self, frames):
        """Implement Stop-and-Wait protocol for sending frames"""
        for frame in frames:
            sent_successfully = False
            attempts = 0
            
            while not sent_successfully and attempts < 3:
                self.logger.info(f"Sending {frame}")
                
                # Send to all connected links
                for link in self.connections:
                    link.transmit(frame, self)
                
                # Simulate waiting for ACK
                time.sleep(TRANSMISSION_DELAY)
                
                # Simulate ACK reception (in real implementation, this would be handled by actual ACK frames)
                # For simulation purposes, we randomly decide if the frame was acknowledged
                if random.random() > BIT_ERROR_RATE:
                    sent_successfully = True
                else:
                    attempts += 1
                    self.logger.warning(f"Frame {frame.sequence_number} timed out, retrying ({attempts}/3)")
                    time.sleep(TRANSMISSION_DELAY)  # Wait before retrying
            
            if not sent_successfully:
                self.logger.error(f"Failed to send frame {frame.sequence_number} after 3 attempts")
                return False
        
        return True
    
    def _send_go_back_n(self, frames):
        """Implement Go-Back-N protocol for sending frames with error control"""
        base = 0  # First unacknowledged frame
        next_seq_num = 0  # Next frame to send
        total_frames = len(frames)
        
        self.logger.info(f"Using Go-Back-N protocol with window size {self.window_size} for {total_frames} frames")
        
        # Start a timer thread to check for timeouts
        stop_timer = threading.Event()
        timer_thread = threading.Thread(target=self._check_timeouts, args=(stop_timer,))
        timer_thread.daemon = True
        timer_thread.start()
        
        try:
            while base < total_frames:
                # Send frames within the window
                while next_seq_num < base + self.window_size and next_seq_num < total_frames:
                    frame = frames[next_seq_num]
                    self.logger.info(f"Sending {frame}")
                    
                    # Store the frame for potential retransmission
                    self.unacknowledged_frames[frame.sequence_number] = (frame, time.time())
                    
                    # Send to all connected links
                    for link in self.connections:
                        link.transmit(frame, self)
                    
                    next_seq_num += 1
                
                # Wait for ACKs - in a real implementation, this would be event-driven
                # For simulation, we'll just wait a bit
                time.sleep(TRANSMISSION_DELAY * 2)
                
                # Check for timeouts in unacknowledged frames
                current_time = time.time()
                timeout_occurred = False
                
                for seq_num in list(self.unacknowledged_frames.keys()):
                    frame, timestamp = self.unacknowledged_frames[seq_num]
                    if current_time - timestamp > self.timeout:
                        self.logger.warning(f"Timeout detected for frame {seq_num}")
                        timeout_occurred = True
                        break
                
                if timeout_occurred:
                    # Reset next_seq_num to retransmit from the base
                    self.logger.info(f"Retransmitting all frames from {base} to {next_seq_num-1}")
                    next_seq_num = base
                else:
                    # Check if base has moved (due to received ACKs)
                    old_base = base
                    while base < total_frames and frames[base].sequence_number not in self.unacknowledged_frames:
                        base += 1
                    
                    # Only log if base has actually moved
                    if base > old_base:
                        self.logger.info(f"Window moved: base is now at frame {base}")
            
            # All frames sent and acknowledged
            self.logger.info(f"All {total_frames} frames sent successfully")
            return True
        
        finally:
            # Stop the timer thread
            stop_timer.set()
            timer_thread.join(timeout=1.0)
    
    def _check_timeouts(self, stop_event):
        """Check for timeouts in unacknowledged frames"""
        while not stop_event.is_set():
            current_time = time.time()
            timed_out_frames = []
            
            # Check for timed out frames
            for seq_num in list(self.unacknowledged_frames.keys()):
                frame, timestamp = self.unacknowledged_frames[seq_num]
                if current_time - timestamp > self.timeout:
                    timed_out_frames.append(seq_num)
            
            # Retransmit timed out frames
            for seq_num in timed_out_frames:
                frame, _ = self.unacknowledged_frames[seq_num]
                self.logger.warning(f"Frame {seq_num} timed out, retransmitting")
                
                # Update timestamp
                self.unacknowledged_frames[seq_num] = (frame, current_time)
                
                # Retransmit to all connected links
                for link in self.connections:
                    link.transmit(frame, self)
            
            # Sleep for a short time before checking again
            time.sleep(0.1)
    
    def receive_message(self, frame, source_device):
        """Process a received frame"""
        # Check if the frame is addressed to this device or is a broadcast
        if frame.destination_mac == str(self.mac_address) or frame.destination_mac == "FF:FF:FF:FF:FF:FF":
            # Check for frame validity using checksum
            if frame.is_valid():
                self.logger.info(f"Received valid frame")
                
                # Handle different frame types
                if frame.type == FrameType.DATA:
                    # Check if this is an IP packet
                    try:
                        packet_data = eval(frame.data)
                        if isinstance(packet_data, dict) and 'source' in packet_data and 'destination' in packet_data:
                            # This is an IP packet
                            packet = IPPacket(
                                packet_data['source'],
                                packet_data['destination'],
                                packet_data['data'],
                                packet_data.get('protocol', 1),
                                packet_data.get('ttl', DEFAULT_TTL)
                            )
                            packet.route_trace = packet_data.get('route_trace', [])
                            packet.add_to_route(self.name, "Device")
                            
                            # If this is the final destination, print route
                            if packet.destination == self.ip_address.address:
                                print(packet.get_route_summary())
                    except:
                        pass  # Not an IP packet, continue with normal processing
                    
                    # Check if this is a size frame
                    if frame.data.startswith("__SIZE__"):
                        try:
                            # Extract the total message size
                            total_size = int(frame.data.split("__SIZE__")[1])
                            self.logger.info(f"Message size received: {total_size} characters")
                            
                            # Initialize or reset the expected message size
                            if not hasattr(self, 'expected_message_sizes'):
                                self.expected_message_sizes = {}
                            self.expected_message_sizes[frame.source_mac] = total_size
                            
                            # Send ACK for the next expected frame (not this one)
                            next_expected = frame.sequence_number + 1
                            ack_frame = Frame(
                                frame.source_mac,
                                str(self.mac_address),
                                f"ACK-{next_expected}",  # ACK for next expected frame
                                type=FrameType.ACK,
                                sequence_number=next_expected - 1  # Use the current frame's sequence number
                            )
                            self.logger.info(f"Sending ACK {next_expected} (expecting frame {next_expected} next)")
                            for link in self.connections:
                                link.transmit(ack_frame, self)
                            
                            # Update expected sequence number
                            self.expected_sequence_number = next_expected
                            
                        except (ValueError, IndexError):
                            self.logger.error(f"Invalid SIZE frame format: {frame.data}")
                    else:
                        # Regular data frame
                        if frame.sequence_number == self.expected_sequence_number:
                            # Frame is in order
                            self._buffer_character(frame.data, str(frame.source_mac), frame.sequence_number)
                            
                            # Update expected sequence number
                            next_expected = self.expected_sequence_number + 1
                            self.expected_sequence_number = next_expected
                            
                            # Send ACK for the next expected frame
                            ack_frame = Frame(
                                frame.source_mac,
                                str(self.mac_address),
                                f"ACK-{next_expected}",  # ACK for next expected frame
                                type=FrameType.ACK,
                                sequence_number=frame.sequence_number  # Use the current frame's sequence number
                            )
                            self.logger.info(f"Sending ACK {next_expected} (expecting frame {next_expected} next)")
                            for link in self.connections:
                                link.transmit(ack_frame, self)
                            
                            # Process any buffered frames that are now in order
                            self._process_buffer()
                            
                            # Check if we've received all characters for this message
                            if hasattr(self, 'expected_message_sizes') and frame.source_mac in self.expected_message_sizes:
                                total_size = self.expected_message_sizes[frame.source_mac]
                                if hasattr(self, 'char_buffers') and frame.source_mac in self.char_buffers:
                                    char_buffer = self.char_buffers[frame.source_mac]
                                    # +1 because we don't count the size frame
                                    if len(char_buffer) >= total_size:
                                        self.logger.info(f"All {total_size} characters received, reassembling message")
                                        self._reassemble_message(frame.source_mac, total_size)
                        else:
                            # Frame is out of order
                            self.logger.warning(f"Received out-of-order frame {frame.sequence_number}, expected {self.expected_sequence_number}")
                            
                            if frame.sequence_number > self.expected_sequence_number:
                                # Buffer the frame for later processing
                                self.buffer.append(frame)
                                self.logger.info(f"Buffered frame {frame.sequence_number}")
                            
                            # Send ACK for the next expected frame (duplicate ACK)
                            # This tells the sender to retransmit from this point
                            ack_frame = Frame(
                                frame.source_mac,
                                str(self.mac_address),
                                f"ACK-{self.expected_sequence_number}",  # Request the expected frame
                                type=FrameType.ACK,
                                sequence_number=self.expected_sequence_number-1
                            )
                            self.logger.info(f"Sending duplicate ACK {self.expected_sequence_number} (still expecting frame {self.expected_sequence_number})")
                            for link in self.connections:
                                link.transmit(ack_frame, self)
                
                elif frame.type == FrameType.ACK:
                    # Process ACK frame
                    # Extract the next expected sequence number from the ACK data
                    try:
                        ack_data = frame.data.split("-")[1]
                        next_expected = int(ack_data)
                        self.logger.info(f"Received ACK {next_expected} (frames up to {next_expected-1} acknowledged)")
                        
                        # Remove all acknowledged frames from the unacknowledged list
                        # This is the cumulative ACK behavior of Go-Back-N
                        for seq_num in list(self.unacknowledged_frames.keys()):
                            if seq_num < next_expected:
                                del self.unacknowledged_frames[seq_num]
                                self.logger.debug(f"Frame {seq_num} acknowledged")
                    except (ValueError, IndexError):
                        self.logger.error(f"Invalid ACK format: {frame.data}")
                
                elif frame.type == FrameType.NAK:
                    # Process NAK frame
                    self.logger.warning(f"Received NAK for frame {frame.sequence_number}")
                    if frame.sequence_number in self.unacknowledged_frames:
                        # Retransmit the frame
                        retransmit_frame, _ = self.unacknowledged_frames[frame.sequence_number]
                        self.logger.info(f"Retransmitting {retransmit_frame}")
                        for link in self.connections:
                            link.transmit(retransmit_frame, self)
                        # Update timestamp
                        self.unacknowledged_frames[frame.sequence_number] = (retransmit_frame, time.time())
            
            else:
                # Frame is corrupted - detected by checksum
                self.logger.warning(f"Received corrupted frame {frame.sequence_number} (checksum mismatch)")
                
                # For Go-Back-N, we don't send NAKs, we just don't ACK the corrupted frame
                # This will cause a timeout at the sender and trigger retransmission
                
                # However, we can send a duplicate ACK for the last correctly received frame
                # to speed up recovery
                if frame.type == FrameType.DATA:
                    # Send duplicate ACK for the last correctly received frame
                    ack_frame = Frame(
                        frame.source_mac,
                        str(self.mac_address),
                        f"ACK-{self.expected_sequence_number}",  # Request the expected frame
                        type=FrameType.ACK,
                        sequence_number=self.expected_sequence_number-1
                    )
                    self.logger.info(f"Sending duplicate ACK {self.expected_sequence_number} due to corrupted frame")
                    for link in self.connections:
                        link.transmit(ack_frame, self)
        else:
            # Frame is not for this device
            self.logger.debug(f"Ignoring frame not addressed to this device")
    
    def _process_buffer(self):
        """Process buffered frames that are now in order"""
        # Sort buffer by sequence number
        self.buffer.sort(key=lambda f: f.sequence_number)
        
        # Process frames that are now in order
        while self.buffer and self.buffer[0].sequence_number == self.expected_sequence_number:
            frame = self.buffer.pop(0)
            self.logger.info(f"Processing buffered frame {frame.sequence_number}")
            self.received_messages.append((frame.data, str(frame.source_mac)))
            self.expected_sequence_number += 1
    
    def __str__(self):
        return f"Device({self.name}, MAC={self.mac_address})"

    def _buffer_character(self, char, source_mac, sequence_number):
        """Buffer a character from a received frame"""
        # Initialize the character buffer for this source if it doesn't exist
        if not hasattr(self, 'char_buffers'):
            self.char_buffers = {}
        
        if source_mac not in self.char_buffers:
            self.char_buffers[source_mac] = {}
        
        # Store the character at its sequence position
        self.char_buffers[source_mac][sequence_number] = char
        self.logger.debug(f"Buffered character '{char}' from {source_mac} at position {sequence_number}")

    def _reassemble_message(self, source_mac, total_size):
        """Reassemble a complete message from buffered characters/chunks"""
        if not hasattr(self, 'char_buffers') or source_mac not in self.char_buffers:
            self.logger.warning(f"No buffer found for {source_mac}")
            return
        
        # Get the buffer for this source
        char_buffer = self.char_buffers[source_mac]
        
        # Check if we have all characters/chunks
        if sum(len(chunk) for chunk in char_buffer.values()) >= total_size:
            # Sort by sequence number and join characters/chunks
            # Skip the first frame (size frame) by filtering sequence numbers
            # that are greater than the size frame's sequence number
            size_frame_seq = min(char_buffer.keys()) - 1  # Estimate the size frame's sequence number
            sorted_chunks = [char_buffer[seq] for seq in sorted(char_buffer.keys()) if seq > size_frame_seq]
            
            # Join all chunks - ensure we don't exceed total_size
            message = ''.join(sorted_chunks)
            message = message[:total_size]  # Truncate to expected size
            
            self.logger.info(f"Reassembled message from {source_mac}: '{message}'")
            self.received_messages.append((message, source_mac))
            
            # Clear the buffer for this source
            self.char_buffers[source_mac] = {}
            
            # Clear the expected message size
            if hasattr(self, 'expected_message_sizes') and source_mac in self.expected_message_sizes:
                del self.expected_message_sizes[source_mac]
        else:
            self.logger.warning(f"Incomplete message from {source_mac}: have {sum(len(chunk) for chunk in char_buffer.values())} of {total_size} characters")


class Hub(Device):
    """Implements a basic hub that broadcasts data to all connected devices."""
    
    def __init__(self, name):
        super().__init__(name)
    
    def receive_message(self, frame, source_device):
        """Receive a message from a link and broadcast it to all other links."""
        self.logger.info(f"Hub broadcasting: {frame}")
        
        # Broadcast to all connections except the source
        for link in self.connections:
            if source_device not in [link.endpoint1, link.endpoint2]:
                link.transmit(frame, self)
    
    def __str__(self):
        return f"Hub({self.name}, MAC={self.mac_address})"


class Bridge(Device):
    """Implements a bridge that forwards frames between network segments."""
    
    def __init__(self, name):
        super().__init__(name)
        # Dictionary to store which MAC addresses are on which interface (connection index)
        self.mac_table = {}
        # Track frames we've already processed to prevent loops
        self.processed_frames = set()
    
    def receive_message(self, frame, source_device):
        """Forward frames based on MAC address."""
        # Create a unique identifier for this frame to prevent processing it multiple times
        frame_id = f"{frame.source_mac}_{frame.destination_mac}_{frame.sequence_number}"
        
        # If we've already processed this frame, ignore it to prevent loops
        if frame_id in self.processed_frames:
            self.logger.debug(f"Already processed {frame}, ignoring to prevent loops")
            return
            
        # Add to processed frames
        self.processed_frames.add(frame_id)
        
        self.logger.info(f"Bridge processing {frame}")
        
        # Learn the source MAC address
        source_link = None
        for i, link in enumerate(self.connections):
            if source_device in [link.endpoint1, link.endpoint2]:
                self.mac_table[frame.source_mac] = i
                source_link = link
                break
        
        # If destination is known, forward only to that port
        if frame.destination_mac in self.mac_table:
            target_index = self.mac_table[frame.destination_mac]
            target_link = self.connections[target_index]
            
            if target_link != source_link:
                self.logger.info(f"Forwarding to known device at port {target_index}")
                target_link.transmit(frame, self)
        else:
            # Destination unknown or broadcast, flood to all ports except the source
            self.logger.info(f"Flooding frame to all ports except source")
            for link in self.connections:
                if link != source_link:
                    link.transmit(frame, self)
    
    def __str__(self):
        return f"Bridge({self.name}, MAC={self.mac_address})"


class Switch(Bridge):
    """Implements a switch that learns MAC addresses and forwards frames intelligently."""
    
    def __init__(self, name):
        super().__init__(name)
        # Additional switch-specific features
        self.collision_domains = 0
        self.broadcast_domains = 1  # A switch forms a single broadcast domain
        self.vlan_table = {}  # VLAN ID -> set of ports
    
    def update_domains(self):
        """Update the count of collision and broadcast domains."""
        # Each port on a switch is a separate collision domain
        self.collision_domains = len(self.connections)
        self.logger.info(f"Switch has {self.collision_domains} collision domains and {len(self.vlan_table) or 1} broadcast domain(s)")
        return self.collision_domains, len(self.vlan_table) or 1
    
    def create_vlan(self, vlan_id, ports):
        """Create a VLAN with the specified ports."""
        if vlan_id in self.vlan_table:
            self.logger.warning(f"VLAN {vlan_id} already exists, updating ports")
        
        self.vlan_table[vlan_id] = set(ports)
        self.logger.info(f"Created VLAN {vlan_id} with ports {ports}")
        
        # Update broadcast domains
        self.broadcast_domains = len(self.vlan_table) or 1
    
    def add_port_to_vlan(self, vlan_id, port):
        """Add a port to a VLAN."""
        if vlan_id not in self.vlan_table:
            self.logger.error(f"VLAN {vlan_id} does not exist")
            return False
        
        self.vlan_table[vlan_id].add(port)
        self.logger.info(f"Added port {port} to VLAN {vlan_id}")
        return True
    
    def remove_port_from_vlan(self, vlan_id, port):
        """Remove a port from a VLAN."""
        if vlan_id not in self.vlan_table:
            self.logger.error(f"VLAN {vlan_id} does not exist")
            return False
        
        if port in self.vlan_table[vlan_id]:
            self.vlan_table[vlan_id].remove(port)
            self.logger.info(f"Removed port {port} from VLAN {vlan_id}")
            return True
        else:
            self.logger.warning(f"Port {port} is not in VLAN {vlan_id}")
            return False
    
    def __str__(self):
        return f"Switch({self.name}, MAC={self.mac_address}, {len(self.connections)} ports)"


class Link:
    """Represents a connection between network devices."""
    
    def __init__(self, name, endpoint1=None, endpoint2=None):
        self.name = name
        self.endpoint1 = endpoint1
        self.endpoint2 = endpoint2
        self.logger = logging.getLogger(f"Link_{name}")
        file_handler = logging.FileHandler(f"logs/link_{name}.log")
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        
        # CSMA/CD properties
        self.medium_busy = False
        self.busy_until = 0  # Time when medium will become free
        self.collision_detected = False
        self.transmitting_devices = set()  # Track devices currently transmitting
        self.transmission_lock = threading.Lock()  # Lock for synchronizing access to medium
        
        # Randomly make the medium busy initially (only 10% chance)
        if random.random() < 0.1:
            busy_duration = random.uniform(0.05, 0.15)
            self.medium_busy = True
            self.busy_until = time.time() + busy_duration
            self.logger.info(f"Medium initially busy for {busy_duration:.3f} seconds")
        
        if endpoint1:
            endpoint1.connect(self)
        if endpoint2:
            endpoint2.connect(self)
    
    def is_medium_busy(self):
        """Check if the medium is busy (carrier sense)"""
        with self.transmission_lock:
            current_time = time.time()
            # Check if the busy time has expired
            if self.medium_busy and current_time > self.busy_until:
                self.medium_busy = False
                self.logger.info(f"Medium is now free (busy time expired)")
            return self.medium_busy
    
    def start_transmission(self, device):
        """Start transmission from a device (returns True if successful, False if collision)"""
        with self.transmission_lock:
            # Check if medium is busy (carrier sense)
            if self.is_medium_busy():
                busy_for = max(0, self.busy_until - time.time())
                self.logger.info(f"{device.name} sensed medium busy, will be busy for {busy_for:.3f} more seconds")
                return False
            
            # Medium is free, start transmitting
            # Set medium busy for a short duration (just for this transmission)
            transmission_duration = random.uniform(0.02, 0.05)  # Shorter duration to avoid getting stuck
            self.medium_busy = True
            self.busy_until = time.time() + transmission_duration
            self.transmitting_devices.add(device)
            self.logger.info(f"{device.name} started transmission, medium is busy for {transmission_duration:.3f} seconds")
            
            # Check for collision (if another device is already transmitting)
            if len(self.transmitting_devices) > 1:
                self.collision_detected = True
                self.logger.warning(f"Collision detected! {len(self.transmitting_devices)} devices transmitting")
                return False
            
            return True
    
    def end_transmission(self, device):
        """End transmission from a device"""
        with self.transmission_lock:
            if device in self.transmitting_devices:
                self.transmitting_devices.remove(device)
                self.logger.info(f"{device.name} ended transmission")
            
            # Reset collision flag if no devices are transmitting
            if len(self.transmitting_devices) == 0:
                self.collision_detected = False
                
                # Set a very short cooldown period
                cooldown = 0.005  # Very short cooldown to avoid getting stuck
                self.busy_until = time.time() + cooldown
                self.logger.info(f"Medium will be free in {cooldown:.3f} seconds")
    
    def connect_endpoint(self, endpoint, position=None):
        """Connect an endpoint (device or hub) to this link."""
        if position == 1 or (position is None and self.endpoint1 is None):
            self.endpoint1 = endpoint
            endpoint.connect(self)
            self.logger.info(f"Connected {endpoint.name} as endpoint1")
        elif position == 2 or (position is None and self.endpoint2 is None):
            self.endpoint2 = endpoint
            endpoint.connect(self)
            self.logger.info(f"Connected {endpoint.name} as endpoint2")
        else:
            raise ValueError("Link already has two endpoints connected")
    
    def disconnect_endpoint(self, endpoint):
        """Disconnect an endpoint from this link."""
        if self.endpoint1 == endpoint:
            self.endpoint1.disconnect(self)
            self.endpoint1 = None
            self.logger.info(f"Disconnected {endpoint.name} from endpoint1")
        elif self.endpoint2 == endpoint:
            self.endpoint2.disconnect(self)
            self.endpoint2 = None
            self.logger.info(f"Disconnected {endpoint.name} from endpoint2")
    
    def transmit(self, frame, source):
        """Transmit a frame from source to the other endpoint with CSMA/CD."""
        if source not in [self.endpoint1, self.endpoint2]:
            self.logger.error(f"Error: Source {source.name} not connected to this link")
            return False
        
        # Determine the destination
        destination = self.endpoint2 if source == self.endpoint1 else self.endpoint1
        
        if destination is None:
            self.logger.error(f"Error: No destination connected")
            return False
        
        # Create a copy of the frame to avoid modifying the original
        transmitted_frame = Frame(
            frame.destination_mac,
            frame.source_mac,
            frame.data,
            frame.type,
            frame.sequence_number
        )
        
        # Simplified CSMA/CD implementation to avoid getting stuck
        attempts = 0
        max_attempts = 5  # Reduced to avoid long waits
        
        while attempts < max_attempts:
            # Randomly make the medium busy to demonstrate CSMA/CD (only 20% chance)
            if random.random() < 0.2:
                self.logger.info(f"Medium is busy when {source.name} tries to send frame {frame.sequence_number}")
                # Wait a short time and try again
                time.sleep(0.05)
                attempts += 1
                continue
            
            # Medium is free, proceed with transmission
            self.logger.info(f"{source.name} transmitting frame {frame.sequence_number} to {destination.name}")
            
            # Simulate transmission delay
            time.sleep(0.02)
            
            # Small chance of collision (10%)
            if random.random() < 0.1:
                self.logger.warning(f"Collision detected during {source.name}'s transmission of frame {frame.sequence_number}")
                # Apply backoff
                backoff_time = random.uniform(0.01, 0.05) * (attempts + 1)
                self.logger.info(f"{source.name} backing off for {backoff_time:.3f}s after collision")
                time.sleep(backoff_time)
                attempts += 1
                continue
            
            # Small chance of corruption (based on ERROR_INJECTION_RATE)
            if random.random() < ERROR_INJECTION_RATE and frame.type == FrameType.DATA:
                self.logger.warning(f"Error introduced in frame {frame.sequence_number}")
                # Introduce error
                transmitted_frame.data = transmitted_frame.data + "_ERROR"
            
            # Successful transmission
            self.logger.info(f"Frame {frame.sequence_number} successfully transmitted from {source.name} to {destination.name}")
            
            # Deliver the frame to the destination
            destination.receive_message(transmitted_frame, source)
            return True
        
        # Max attempts reached
        self.logger.error(f"{source.name} exceeded maximum transmission attempts ({max_attempts}) for frame {frame.sequence_number}")
        return False
    
    def detect_collision(self, device):
        """Check if a collision has occurred during transmission"""
        with self.transmission_lock:
            # A collision occurs if more than one device is transmitting
            collision = len(self.transmitting_devices) > 1
            if collision and not self.collision_detected:
                self.collision_detected = True
                self.logger.warning(f"Collision detected during {device.name}'s transmission!")
            return collision
    
    def __str__(self):
        endpoint1_name = self.endpoint1.name if self.endpoint1 else "None"
        endpoint2_name = self.endpoint2.name if self.endpoint2 else "None"
        return f"Link({self.name}, {endpoint1_name} <-> {endpoint2_name})"


class Network:
    MAX_PACKETS = 30
    
    def __init__(self, name):
        self.name = name
        self.devices = {}
        self.hubs = {}
        self.bridges = {}
        self.switches = {}
        self.routers = {}
        self.links = {}
        self.packet_count = 0
        self.logger = logging.getLogger(f"Network_{name}")
        file_handler = logging.FileHandler(f"logs/network_{name}.log")
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
    
    def configure_router(self, router_name: str, interface_configs: list) -> bool:
        """Configure interfaces and routes on a router.
        
        Args:
            router_name: Name of the router to configure
            interface_configs: List of interface configurations, each containing:
                - name: Interface name
                - ip_address: IP address for the interface
                - subnet_mask: Subnet mask for the interface
                - routes: List of route configurations, each containing:
                    - destination: Destination network
                    - next_hop: Next hop IP address
                    - subnet_mask: Subnet mask for the route
        
        Returns:
            bool: True if configuration was successful, False otherwise
        """
        router = self.routers.get(router_name)
        if not router:
            self.logger.error(f"Router '{router_name}' not found")
            return False
        
        try:
            for config in interface_configs:
                # Add interface
                interface = router.add_interface(
                    config['name'],
                    config['ip_address'],
                    config['subnet_mask']
                )
                
                # Add routes for this interface
                if 'routes' in config:
                    for route in config['routes']:
                        router.add_route(
                            route['destination'],
                            route['next_hop'],
                            route['subnet_mask'],
                            config['name']
                        )
            
            self.logger.info(f"Successfully configured router {router_name} with {len(interface_configs)} interfaces")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring router {router_name}: {str(e)}")
            return False
    
    def add_device(self, name, ip_address=None, subnet_mask=None, default_gateway=None):
        """Add a new device to the network with optional IP configuration."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches or name in self.routers:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        device = Device(name)
        if ip_address and subnet_mask:
            device.configure_network(ip_address, subnet_mask, default_gateway)
        
        self.devices[name] = device
        self.logger.info(f"Added device: {name} with IP {ip_address or 'unconfigured'}")
        return device
    
    def add_hub(self, name):
        """Add a new hub to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches or name in self.routers:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        hub = Hub(name)
        self.hubs[name] = hub
        self.logger.info(f"Added hub: {name}")
        return hub
    
    def add_bridge(self, name):
        """Add a new bridge to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches or name in self.routers:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        bridge = Bridge(name)
        self.bridges[name] = bridge
        self.logger.info(f"Added bridge: {name}")
        return bridge
    
    def add_switch(self, name):
        """Add a new switch to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches or name in self.routers:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        switch = Switch(name)
        self.switches[name] = switch
        self.logger.info(f"Added switch: {name}")
        return switch
    
    def add_router(self, name):
        """Add a new router to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches or name in self.routers:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        router = Router(name)
        self.routers[name] = router
        self.logger.info(f"Added router: {name}")
        return router
    
    def add_link(self, name, endpoint1_name=None, endpoint2_name=None):
        """Add a new link between two endpoints (devices or hubs)."""
        if name in self.links:
            self.logger.error(f"A link with name '{name}' already exists")
            return None
        
        endpoint1 = None
        endpoint2 = None
        
        if endpoint1_name:
            endpoint1 = (self.devices.get(endpoint1_name) or 
                         self.hubs.get(endpoint1_name) or 
                         self.bridges.get(endpoint1_name) or 
                         self.switches.get(endpoint1_name) or
                         self.routers.get(endpoint1_name))
            if not endpoint1:
                self.logger.error(f"Endpoint '{endpoint1_name}' not found")
                return None
        
        if endpoint2_name:
            endpoint2 = (self.devices.get(endpoint2_name) or 
                         self.hubs.get(endpoint2_name) or 
                         self.bridges.get(endpoint2_name) or 
                         self.switches.get(endpoint2_name) or
                         self.routers.get(endpoint2_name))
            if not endpoint2:
                self.logger.error(f"Endpoint '{endpoint2_name}' not found")
                return None
        
        link = Link(name, endpoint1, endpoint2)
        self.links[name] = link
        self.logger.info(f"Added link: {name} connecting {endpoint1_name or 'None'} and {endpoint2_name or 'None'}")
        return link
    
    def remove_device(self, name):
        """Remove a device from the network."""
        if name not in self.devices:
            self.logger.error(f"Device '{name}' not found")
            return False
        
        device = self.devices[name]
        
        # Disconnect from all links
        for link in device.connections.copy():
            link.disconnect_endpoint(device)
        
        del self.devices[name]
        self.logger.info(f"Removed device: {name}")
        return True
    
    def remove_hub(self, name):
        """Remove a hub from the network."""
        if name not in self.hubs:
            self.logger.error(f"Hub '{name}' not found")
            return False
        
        hub = self.hubs[name]
        
        # Disconnect from all links
        for link in hub.connections.copy():
            link.disconnect_endpoint(hub)
        
        del self.hubs[name]
        self.logger.info(f"Removed hub: {name}")
        return True
    
    def remove_bridge(self, name):
        """Remove a bridge from the network."""
        if name not in self.bridges:
            self.logger.error(f"Bridge '{name}' not found")
            return False
        
        bridge = self.bridges[name]
        
        # Disconnect from all links
        for link in bridge.connections.copy():
            link.disconnect_endpoint(bridge)
        
        del self.bridges[name]
        self.logger.info(f"Removed bridge: {name}")
        return True
    
    def remove_switch(self, name):
        """Remove a switch from the network."""
        if name not in self.switches:
            self.logger.error(f"Switch '{name}' not found")
            return False
        
        switch = self.switches[name]
        
        # Disconnect from all links
        for link in switch.connections.copy():
            link.disconnect_endpoint(switch)
        
        del self.switches[name]
        self.logger.info(f"Removed switch: {name}")
        return True
    
    def remove_router(self, name):
        """Remove a router from the network."""
        if name not in self.routers:
            self.logger.error(f"Router '{name}' not found")
            return False
        
        router = self.routers[name]
        
        # Disconnect from all links
        for link in router.connections.copy():
            link.disconnect_endpoint(router)
        
        del self.routers[name]
        self.logger.info(f"Removed router: {name}")
        return True
    
    def remove_link(self, name):
        """Remove a link from the network."""
        if name not in self.links:
            self.logger.error(f"Link '{name}' not found")
            return False
        
        link = self.links[name]
        
        # Disconnect endpoints
        if link.endpoint1:
            link.disconnect_endpoint(link.endpoint1)
        if link.endpoint2:
            link.disconnect_endpoint(link.endpoint2)
        
        del self.links[name]
        self.logger.info(f"Removed link: {name}")
        return True
    
    def send_message(self, source_name, message, target_name=None, target_ip=None):
        if self.packet_count >= self.MAX_PACKETS:
            self.logger.warning(f"Maximum packet limit ({self.MAX_PACKETS}) reached. Message not sent.")
            return False
            
        source = (self.devices.get(source_name) or 
                  self.hubs.get(source_name) or 
                  self.bridges.get(source_name) or 
                  self.switches.get(source_name) or
                  self.routers.get(source_name))
        
        if not source:
            self.logger.error(f"Source device '{source_name}' not found")
            return False
        
        target = None
        target_mac = None
        
        if target_name:
            target = (self.devices.get(target_name) or 
                      self.hubs.get(target_name) or 
                      self.bridges.get(target_name) or 
                      self.switches.get(target_name) or
                      self.routers.get(target_name))
            
            if not target:
                self.logger.error(f"Target device '{target_name}' not found")
                return False
            
            target_mac = str(target.mac_address)
        
        success = source.send_message(message, target_mac, target_ip)
        if success:
            self.packet_count += 1
            if self.packet_count >= Network.MAX_PACKETS:
                self.logger.info(f"Reached maximum packet limit ({Network.MAX_PACKETS})")
        return success
    
    def display_network(self):
        """Display the current network topology."""
        print(f"\n=== Network: {self.name} ===")
        
        print("\nDevices:")
        for name, device in self.devices.items():
            ip_info = f", IP: {device.ip_address}" if device.ip_address else ""
            print(f"  {name} (MAC: {device.mac_address}{ip_info})")
        
        print("\nRouters:")
        for name, router in self.routers.items():
            print(f"  {name} (MAC: {router.mac_address})")
            if router.interfaces:
                print("    Interfaces:")
                for iface_name, iface in router.interfaces.items():
                    print(f"      {iface}")
            if router.routing_table.routes:
                print("    Routes:")
                for route in router.routing_table.routes:
                    print(f"      {route}")
        
        print("\nHubs:")
        for name, hub in self.hubs.items():
            print(f"  {name} (MAC: {hub.mac_address})")
        
        print("\nBridges:")
        for name, bridge in self.bridges.items():
            print(f"  {name} (MAC: {bridge.mac_address})")
            if bridge.mac_table:
                print("    MAC Table:")
                for mac, port in bridge.mac_table.items():
                    print(f"      {mac} -> Port {port}")
        
        print("\nSwitches:")
        for name, switch in self.switches.items():
            print(f"  {name} (MAC: {switch.mac_address})")
            if switch.mac_table:
                print("    MAC Table:")
                for mac, port in switch.mac_table.items():
                    print(f"      {mac} -> Port {port}")
            if switch.vlan_table:
                print("    VLANs:")
                for vlan_id, ports in switch.vlan_table.items():
                    print(f"      VLAN {vlan_id}: Ports {sorted(ports)}")
        
        print("\nLinks:")
        for name, link in self.links.items():
            endpoint1_name = link.endpoint1.name if link.endpoint1 else "None"
            endpoint2_name = link.endpoint2.name if link.endpoint2 else "None"
            print(f"  {name}: {endpoint1_name} <-> {endpoint2_name}")
        
        print("\n")
    
    def __str__(self):
        return (f"Network({self.name}, {len(self.devices)} devices, {len(self.routers)} routers, "
                f"{len(self.hubs)} hubs, {len(self.bridges)} bridges, "
                f"{len(self.switches)} switches, {len(self.links)} links)")


def demonstrate_ip_networking():
    """Demonstrate IP networking and routing capabilities"""
    print("\n=== IP Networking and Routing Demonstration ===")
    
    # Create a network
    network = Network("IP_Demo")
    
    # Create devices with IP addresses
    pc1 = network.add_device("PC1", "192.168.1.10", "255.255.255.0", "192.168.1.1")
    pc2 = network.add_device("PC2", "192.168.1.11", "255.255.255.0", "192.168.1.1")
    pc3 = network.add_device("PC3", "192.168.2.10", "255.255.255.0", "192.168.2.1")
    pc4 = network.add_device("PC4", "192.168.2.11", "255.255.255.0", "192.168.2.1")
    
    # Create a router
    router = network.add_router("Router1")
    
    # Configure router interfaces and routes
    network.configure_router("Router1", [
        {
            "name": "eth0",
            "ip_address": "192.168.1.1",
            "subnet_mask": "255.255.255.0",
            "routes": [
                {
                    "destination": "192.168.1.0",
                    "next_hop": "0.0.0.0",  # Direct connection
                    "subnet_mask": "255.255.255.0"
                },
                {
                    "destination": "0.0.0.0",  # Default route
                    "next_hop": "192.168.1.1",
                    "subnet_mask": "0.0.0.0"
                }
            ]
        },
        {
            "name": "eth1",
            "ip_address": "192.168.2.1",
            "subnet_mask": "255.255.255.0",
            "routes": [
                {
                    "destination": "192.168.2.0",
                    "next_hop": "0.0.0.0",  # Direct connection
                    "subnet_mask": "255.255.255.0"
                },
                {
                    "destination": "0.0.0.0",  # Default route
                    "next_hop": "192.168.2.1",
                    "subnet_mask": "0.0.0.0"
                }
            ]
        }
    ])
    
    # Create links
    link1 = network.add_link("Link1", "PC1", "Router1")
    link2 = network.add_link("Link2", "PC2", "Router1")
    link3 = network.add_link("Link3", "PC3", "Router1")
    link4 = network.add_link("Link4", "PC4", "Router1")
    
    # Display network configuration
    network.display_network()
    
    print("\nTesting communication within the same subnet (PC1 -> PC2)...")
    network.send_message("PC1", "Hello PC2!", target_ip="192.168.1.11")
    
    print("\nTesting communication across subnets (PC1 -> PC3)...")
    network.send_message("PC1", "Hello PC3!", target_ip="192.168.2.10")
    
    print("\nTesting routing table lookups...")
    # Get router instance
    router = network.routers["Router1"]
    
    # Test route lookups
    test_destinations = [
        "192.168.1.10",  # PC1
        "192.168.2.10",  # PC3
        "192.168.3.1",   # Unknown network
    ]
    
    for dest in test_destinations:
        route = router.routing_table.lookup(dest)
        if route:
            print(f"Route to {dest}: {route}")
            print(f"Packet would traverse: Source -> MainRouter({route.interface}) -> {dest}")
        else:
            print(f"No route found for {dest}")
    
    print("\nIP Networking Demonstration Complete")
    return network


def interactive_cli():
    """Provide an interactive command-line interface for the network simulator."""
    network = Network("TestNetwork")
    
    print("TCP/IP Network Simulator")
    print("Type 'help' for a list of commands")
    
    while True:
        command = input("\nEnter command: ").strip().lower()
        parts = command.split()
        
        if not parts:
            continue
        
        if parts[0] == "exit" or parts[0] == "quit":
            print("Exiting simulator...")
            break
        
        elif parts[0] == "help":
            print("\nAvailable commands:")
            print("  add device <name> [ip] [mask] [gateway] - Add a new device with optional IP config")
            print("  add hub <name>              - Add a new hub")
            print("  add bridge <name>           - Add a new bridge")
            print("  add switch <name>           - Add a new switch")
            print("  add router <name>           - Add a new router")
            print("  add link <name> [dev1] [dev2] - Add a new link between devices")
            print("  remove device <name>        - Remove a device")
            print("  remove hub <name>           - Remove a hub")
            print("  remove bridge <name>        - Remove a bridge")
            print("  remove switch <name>        - Remove a switch")
            print("  remove router <name>        - Remove a router")
            print("  remove link <name>          - Remove a link")
            print("  connect <link> <endpoint>   - Connect an endpoint to a link")
            print("  disconnect <link> <endpoint> - Disconnect an endpoint from a link")
            print("  send <source> <message> [target] [target_ip] - Send a message")
            print("  display                     - Display network topology")
            print("  demo error                  - Demonstrate error control")
            print("  demo csmacd                 - Demonstrate CSMA/CD protocol")
            print("  demo ip                     - Demonstrate IP networking")
            print("  help                        - Show this help message")
            print("  exit/quit                   - Exit the simulator")
        
        elif parts[0] == "add":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            if parts[1] == "device":
                if len(parts) >= 6:
                    network.add_device(parts[2], parts[3], parts[4], parts[5])
                elif len(parts) >= 5:
                    network.add_device(parts[2], parts[3], parts[4])
                else:
                    network.add_device(parts[2])
            
            elif parts[1] == "hub":
                network.add_hub(parts[2])
            
            elif parts[1] == "bridge":
                network.add_bridge(parts[2])
            
            elif parts[1] == "switch":
                network.add_switch(parts[2])
            
            elif parts[1] == "router":
                network.add_router(parts[2])
            
            elif parts[1] == "link":
                if len(parts) == 3:
                    network.add_link(parts[2])
                elif len(parts) == 4:
                    network.add_link(parts[2], parts[3])
                elif len(parts) >= 5:
                    network.add_link(parts[2], parts[3], parts[4])
            
            else:
                print(f"Error: Unknown entity type '{parts[1]}'")
        
        elif parts[0] == "remove":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            if parts[1] == "device":
                network.remove_device(parts[2])
            
            elif parts[1] == "hub":
                network.remove_hub(parts[2])
            
            elif parts[1] == "bridge":
                network.remove_bridge(parts[2])
            
            elif parts[1] == "switch":
                network.remove_switch(parts[2])
            
            elif parts[1] == "router":
                network.remove_router(parts[2])
            
            elif parts[1] == "link":
                network.remove_link(parts[2])
            
            else:
                print(f"Error: Unknown entity type '{parts[1]}'")
        
        elif parts[0] == "connect":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            link_name = parts[1]
            endpoint_name = parts[2]
            
            if link_name not in network.links:
                print(f"Error: Link '{link_name}' not found")
                continue
            
            endpoint = (network.devices.get(endpoint_name) or 
                        network.hubs.get(endpoint_name) or 
                        network.bridges.get(endpoint_name) or 
                        network.switches.get(endpoint_name) or
                        network.routers.get(endpoint_name))
            
            if not endpoint:
                print(f"Error: Endpoint '{endpoint_name}' not found")
                continue
            
            link = network.links[link_name]
            try:
                link.connect_endpoint(endpoint)
                print(f"Connected {endpoint_name} to {link_name}")
            except ValueError as e:
                print(f"Error: {e}")
        
        elif parts[0] == "disconnect":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            link_name = parts[1]
            endpoint_name = parts[2]
            
            if link_name not in network.links:
                print(f"Error: Link '{link_name}' not found")
                continue
            
            endpoint = (network.devices.get(endpoint_name) or 
                        network.hubs.get(endpoint_name) or 
                        network.bridges.get(endpoint_name) or 
                        network.switches.get(endpoint_name) or
                        network.routers.get(endpoint_name))
            
            if not endpoint:
                print(f"Error: Endpoint '{endpoint_name}' not found")
                continue
            
            link = network.links[link_name]
            link.disconnect_endpoint(endpoint)
            print(f"Disconnected {endpoint_name} from {link_name}")
        
        elif parts[0] == "send":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            source_name = parts[1]
            message = parts[2]
            target_name = parts[3] if len(parts) > 3 else None
            target_ip = parts[4] if len(parts) > 4 else None
            
            network.send_message(source_name, message, target_name, target_ip)
        
        elif parts[0] == "demo" and parts[1] == "ip":
            demonstrate_ip_networking()
        
        elif parts[0] == "demo" and parts[1] == "error":
            demonstrate_error_control()
        
        elif parts[0] == "demo" and parts[1] == "csmacd":
            demonstrate_csma_cd()
        
        elif parts[0] == "display":
            network.display_network()
            
        else:
            print(f"Error: Unknown command '{parts[0]}'")


def demonstrate_error_control():
    """Demonstrate error control in the network simulator"""
    print("\n=== Error Control Demonstration ===")
    
    # Create a network
    network = Network("ErrorControlDemo")
    
    # Create devices
    pc1 = network.add_device("PC1")
    pc2 = network.add_device("PC2")
    
    # Create a link between devices
    link = network.add_link("Link1", "PC1", "PC2")
    
    # Enable Go-Back-N for PC1
    network.enable_go_back_n("PC1", window_size=4)
    
    # Display the network
    network.display_network()
    
    # Send a message from PC1 to PC2
    print("\nSending message from PC1 to PC2 with error control...")
    print(f"Error injection rate: {ERROR_INJECTION_RATE*100}%")
    network.send_message("PC1", "This is a test message with error control!", "PC2")
    
    # Display received messages
    print("\nMessages received by PC2:")
    for data, source in pc2.received_messages:
        print(f"  '{data}' from {source}")
    
    return network


def demonstrate_csma_cd():
    """Demonstrate CSMA/CD protocol in the network simulator"""
    print("\n=== CSMA/CD Protocol Demonstration ===")
    print(f"Medium busy time range: {BUSY_TIME_RANGE[0]:.2f} to {BUSY_TIME_RANGE[1]:.2f} seconds")
    print(f"Backoff slot time: {CSMA_CD_SLOT_TIME:.3f} seconds")
    print(f"Maximum transmission attempts: {CSMA_CD_MAX_ATTEMPTS}")
    
    # Create a network
    network = Network("CSMA_CD_Demo")
    
    # Create devices
    pc1 = network.add_device("PC1")
    pc2 = network.add_device("PC2")
    # Reduced to just 2 PCs for simpler demonstration
    
    # Create a hub to simulate a shared medium
    hub = network.add_hub("Hub1")
    
    # Connect devices to the hub
    link1 = network.add_link("Link1", "PC1", "Hub1")
    link2 = network.add_link("Link2", "PC2", "Hub1")
    
    # Display the network
    network.display_network()
    
    # Simulate fewer concurrent transmissions for a clearer demonstration
    print("\nSimulating concurrent transmissions with CSMA/CD...")
    print("This will demonstrate how devices detect collisions and use backoff algorithms")
    
    # Define a function to send messages with a delay
    def delayed_send(delay, source, message, target):
        print(f"Scheduling {source} to send message in {delay:.2f} seconds")
        time.sleep(delay)
        print(f"{source} attempting to send: '{message}'")
        network.send_message(source, message, target)
    
    # Start just two transmissions with overlapping timing to create collision scenarios
    threads = []
    
    # First transmission
    t1 = threading.Thread(target=delayed_send, args=(0.1, "PC1", "Message from PC1", "PC2"))
    threads.append(t1)
    
    # Second transmission (specifically timed to collide with first)
    t2 = threading.Thread(target=delayed_send, args=(0.15, "PC2", "Message from PC2", "PC1"))
    threads.append(t2)
    
    # Start all threads
    for t in threads:
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    # ...existing code...


class ARPEntry:
    """Represents an entry in the ARP table"""
    def __init__(self, ip_address: str, mac_address: str, interface: str):
        self.ip_address = ip_address
        self.mac_address = mac_address
        self.interface = interface
        self.timestamp = time.time()
        self.is_static = False
    
    def __str__(self):
        entry_type = "static" if self.is_static else "dynamic"
        return f"{self.ip_address} -> {self.mac_address} ({entry_type}) on {self.interface}"

class ARPTable:
    """Implements an ARP table for IP to MAC address resolution"""
    
    def __init__(self, timeout: int = 300, max_entries: int = 1000):
        self.entries: Dict[str, ARPEntry] = {}
        self.timeout = timeout
        self.max_entries = max_entries
        self.logger = logging.getLogger("ARPTable")
        self.last_cleanup = time.time()
        self.cleanup_interval = 60  # Cleanup every 60 seconds
    
    def add_entry(self, ip_address: str, mac_address: str, interface: str, is_static: bool = False):
        """Add an entry to the ARP table"""
        # Check if we need to clean up old entries
        self._maybe_cleanup()
        
        # If table is full and this is a dynamic entry, remove oldest dynamic entry
        if len(self.entries) >= self.max_entries and not is_static:
            self._remove_oldest_dynamic_entry()
        
        entry = ARPEntry(ip_address, mac_address, interface)
        entry.is_static = is_static
        self.entries[ip_address] = entry
        self.logger.info(f"Added ARP entry: {entry}")
    
    def get_mac(self, ip_address: str) -> Optional[str]:
        """Get MAC address for an IP address"""
        self._maybe_cleanup()
        entry = self.entries.get(ip_address)
        if entry:
            # Update timestamp on access for dynamic entries
            if not entry.is_static:
                entry.timestamp = time.time()
            return entry.mac_address
        return None
    
    def remove_entry(self, ip_address: str) -> bool:
        """Remove an entry from the ARP table"""
        if ip_address in self.entries:
            entry = self.entries.pop(ip_address)
            self.logger.info(f"Removed ARP entry: {entry}")
            return True
        return False
    
    def _maybe_cleanup(self):
        """Check if cleanup is needed and perform it if necessary"""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_expired()
            self.last_cleanup = current_time
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired = []
        for ip, entry in self.entries.items():
            if not entry.is_static and current_time - entry.timestamp > self.timeout:
                expired.append(ip)
        
        for ip in expired:
            del self.entries[ip]
            self.logger.info(f"Removed expired ARP entry for {ip}")
    
    def _remove_oldest_dynamic_entry(self):
        """Remove the oldest dynamic entry from the table"""
        oldest_time = float('inf')
        oldest_ip = None
        
        for ip, entry in self.entries.items():
            if not entry.is_static and entry.timestamp < oldest_time:
                oldest_time = entry.timestamp
                oldest_ip = ip
        
        if oldest_ip:
            self.remove_entry(oldest_ip)
    
    def get_all_entries(self) -> List[ARPEntry]:
        """Get all entries in the ARP table"""
        self._maybe_cleanup()
        return list(self.entries.values())
    
    def clear_dynamic_entries(self):
        """Clear all dynamic entries from the table"""
        dynamic_ips = [ip for ip, entry in self.entries.items() if not entry.is_static]
        for ip in dynamic_ips:
            self.remove_entry(ip)
        self.logger.info("Cleared all dynamic ARP entries")
    
    def __str__(self) -> str:
        entries_str = "\n".join(str(entry) for entry in self.entries.values())
        return f"ARP Table ({len(self.entries)} entries):\n{entries_str}"

class RIPUpdate:
    """Represents a RIP routing update"""
    def __init__(self, network: str, subnet_mask: str, next_hop: str, metric: int):
        self.network = network
        self.subnet_mask = subnet_mask
        self.next_hop = next_hop
        self.metric = min(metric, 16)  # RIP metric limit is 16 (infinity)
    
    def __str__(self):
        return f"{self.network}/{self.subnet_mask} via {self.next_hop} metric {self.metric}"

class Router(Device):
    """Implements a router with IP routing capabilities"""
    
    def __init__(self, name):
        super().__init__(name)
        self.routing_table = RoutingTable()
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.arp_table = ARPTable()
        self.rip_enabled = False
        self.rip_routes: Dict[str, RIPUpdate] = {}
        self.rip_timer = None
        self.router_id = str(uuid.uuid4())[:8]  # Unique router ID for routing protocols
    
    def add_interface(self, name: str, ip_address: str, subnet_mask: str) -> NetworkInterface:
        """Add a network interface to the router"""
        interface = NetworkInterface(name, ip_address, subnet_mask)
        self.interfaces[name] = interface
        self.logger.info(f"Added interface: {interface}")
        return interface
    
    def remove_interface(self, name: str) -> bool:
        """Remove a network interface from the router"""
        if name in self.interfaces:
            interface = self.interfaces.pop(name)
            self.logger.info(f"Removed interface: {interface}")
            return True
        return False
    
    def add_route(self, destination: str, next_hop: str, subnet_mask: str,
                 interface: str, metric: int = 1) -> None:
        """Add a route to the routing table"""
        self.routing_table.add_route(destination, next_hop, subnet_mask, interface, metric)
        self.logger.info(f"Added route to {destination}/{subnet_mask} via {next_hop}")
    
    def enable_rip(self):
        """Enable RIP routing protocol"""
        self.rip_enabled = True
        self.start_rip_updates()
        self.logger.info("RIP routing enabled")
    
    def disable_rip(self):
        """Disable RIP routing protocol"""
        self.rip_enabled = False
        if self.rip_timer:
            self.rip_timer.cancel()
        self.logger.info("RIP routing disabled")
    
    def start_rip_updates(self):
        """Start periodic RIP updates"""
        if not self.rip_enabled:
            return
        
        self.send_rip_updates()
        # Schedule next update in 30 seconds
        self.rip_timer = threading.Timer(30.0, self.start_rip_updates)
        self.rip_timer.daemon = True
        self.rip_timer.start()
    
    def send_rip_updates(self):
        """Send RIP updates to neighbors"""
        if not self.rip_enabled:
            return
        
        updates = []
        # Add directly connected networks
        for iface_name, iface in self.interfaces.items():
            updates.append(RIPUpdate(
                iface.ip.network_address,
                iface.ip.subnet,
                "0.0.0.0",  # Direct connection
                1
            ))
        
        # Add routes from routing table
        for route in self.routing_table.routes:
            if route.next_hop != "0.0.0.0":  # Not directly connected
                updates.append(RIPUpdate(
                    str(route.destination.network_address),
                    route.subnet_mask,
                    route.next_hop,
                    route.metric + 1
                ))
        
        # Send updates to all interfaces
        for iface_name, iface in self.interfaces.items():
            # Create RIP message
            rip_msg = {
                "router_id": self.router_id,
                "updates": [(u.network, u.subnet_mask, u.next_hop, u.metric) for u in updates]
            }
            
            # Create IP packet with RIP message
            packet = IPPacket(
                iface.ip.address,
                "224.0.0.9",  # RIP multicast address
                str(rip_msg),
                protocol=520  # RIP protocol number
            )
            
            # Send to all neighbors on this interface
            self.send_message(str(packet), target_ip="224.0.0.9")
    
    def process_rip_update(self, source_ip: str, rip_msg: dict):
        """Process received RIP update"""
        if not self.rip_enabled:
            return
        
        updates_processed = 0
        for network, mask, next_hop, metric in rip_msg["updates"]:
            if metric < 16:  # Valid metric
                # Use source IP as next hop for all routes
                route_key = f"{network}/{mask}"
                new_metric = metric + 1
                
                existing_route = self.routing_table.lookup(network)
                if not existing_route or existing_route.metric > new_metric:
                    # Add or update route
                    self.routing_table.add_route(
                        network,
                        source_ip,
                        mask,
                        self.get_interface_for_ip(source_ip).name,
                        new_metric
                    )
                    updates_processed += 1
        
        if updates_processed > 0:
            self.logger.info(f"Processed {updates_processed} RIP updates from {source_ip}")
    
    def get_interface_for_ip(self, ip_address: str) -> Optional[NetworkInterface]:
        """Find the interface that can reach the given IP address"""
        for iface in self.interfaces.values():
            if iface.is_in_network(ip_address):
                return iface
        return None
    
    def arp_request(self, target_ip: str, interface_name: str) -> Optional[str]:
        """Send ARP request to resolve IP to MAC address"""
        # Check ARP cache first
        mac = self.arp_table.get_mac(target_ip)
        if mac:
            return mac
        
        # Create ARP request
        request = {
            "type": "ARP_REQUEST",
            "source_ip": self.interfaces[interface_name].ip.address,
            "source_mac": str(self.mac_address),
            "target_ip": target_ip
        }
        
        # Broadcast ARP request
        frame = Frame(
            str(self.mac_address),
            "FF:FF:FF:FF:FF:FF",
            str(request),
            self.next_sequence_number
        )
        
        # Send on specified interface
        for link in self.connections:
            if interface_name in str(link):
                link.transmit(frame, self)
                break
        
        # In real implementation, would wait for response
        # For simulation, return None to indicate address not resolved
        return None
    
    def process_arp_message(self, frame: Frame, source_device: 'Device'):
        """Process ARP request or reply"""
        try:
            arp_msg = eval(frame.data)
            if not isinstance(arp_msg, dict) or "type" not in arp_msg:
                return
            
            if arp_msg["type"] == "ARP_REQUEST":
                # Check if we're the target
                for iface in self.interfaces.values():
                    if iface.ip.address == arp_msg["target_ip"]:
                        # Send ARP reply
                        reply = {
                            "type": "ARP_REPLY",
                            "source_ip": iface.ip.address,
                            "source_mac": str(self.mac_address),
                            "target_ip": arp_msg["source_ip"],
                            "target_mac": arp_msg["source_mac"]
                        }
                        
                        reply_frame = Frame(
                            str(self.mac_address),
                            arp_msg["source_mac"],
                            str(reply),
                            frame.sequence_number
                        )
                        
                        # Send reply
                        for link in self.connections:
                            if source_device in [link.endpoint1, link.endpoint2]:
                                link.transmit(reply_frame, self)
                                break
                        
                        return
            
            elif arp_msg["type"] == "ARP_REPLY":
                # Update ARP table
                if arp_msg["target_ip"] == self.interfaces[frame.interface].ip.address:
                    self.arp_table.add_entry(
                        arp_msg["source_ip"],
                        arp_msg["source_mac"],
                        frame.interface
                    )
        
        except Exception as e:
            self.logger.error(f"Error processing ARP message: {e}")
    
    def route_packet(self, packet: IPPacket) -> Optional[Tuple[str, str]]:
        """Route an IP packet and return (next_hop, interface_name) or None if no route"""
        if not packet.is_valid():
            self.logger.warning(f"Invalid packet received: {packet}")
            return None
        
        # Add router to packet route trace
        packet.add_to_route(self.name, "Router")
        
        # Decrement TTL
        if not packet.decrement_ttl():
            self.logger.warning(f"Packet dropped due to TTL expiration: {packet}")
            return None
        
        # Find the best route using longest prefix match
        route = self.routing_table.lookup(packet.destination)
        if not route:
            self.logger.warning(f"No route to destination: {packet.destination}")
            return None
        
        # Add interface information to route trace
        packet.add_to_route(self.name, "Router", route.interface)
        
        # Resolve next hop MAC address using ARP
        next_hop_ip = route.next_hop if route.next_hop != "0.0.0.0" else packet.destination
        next_hop_mac = self.arp_table.get_mac(next_hop_ip)
        
        if not next_hop_mac:
            # Try to resolve MAC address
            next_hop_mac = self.arp_request(next_hop_ip, route.interface)
            if not next_hop_mac:
                self.logger.warning(f"Could not resolve MAC address for {next_hop_ip}")
                return None
        
        return next_hop_ip, route.interface, next_hop_mac


def run_network_test():
    print("\n=== Network Layer Test Case ===")
    print(f"Creating a network with two subnets connected by a router...")
    
    net = Network("TestNetwork")
    
    print("\nCreating devices in subnet 192.168.1.0/24...")
    server = net.add_device("Server", "192.168.1.100", "255.255.255.0", "192.168.1.1")
    client1 = net.add_device("Client1", "192.168.1.101", "255.255.255.0", "192.168.1.1")
    client2 = net.add_device("Client2", "192.168.1.102", "255.255.255.0", "192.168.1.1")
    
    print("\nCreating devices in subnet 192.168.2.0/24...")
    workstation1 = net.add_device("Workstation1", "192.168.2.101", "255.255.255.0", "192.168.2.1")
    workstation2 = net.add_device("Workstation2", "192.168.2.102", "255.255.255.0", "192.168.2.1")
    
    print("\nCreating and configuring router...")
    router = net.add_router("MainRouter")
    
    net.configure_router("MainRouter", [
        {
            "name": "eth0",
            "ip_address": "192.168.1.1",
            "subnet_mask": "255.255.255.0",
            "routes": [
                {
                    "destination": "192.168.1.0",
                    "next_hop": "0.0.0.0",
                    "subnet_mask": "255.255.255.0"
                }
            ]
        },
        {
            "name": "eth1",
            "ip_address": "192.168.2.1",
            "subnet_mask": "255.255.255.0",
            "routes": [
                {
                    "destination": "192.168.2.0",
                    "next_hop": "0.0.0.0",
                    "subnet_mask": "255.255.255.0"
                }
            ]
        }
    ])
    
    print("\nCreating network links...")
    net.add_link("Link1", "Server", "MainRouter")
    net.add_link("Link2", "Client1", "MainRouter")
    net.add_link("Link3", "Client2", "MainRouter")
    net.add_link("Link4", "Workstation1", "MainRouter")
    net.add_link("Link5", "Workstation2", "MainRouter")
    
    print("\nNetwork topology:")
    net.display_network()
    
    print("\n=== Running Test Cases with Route Tracing ===")
    
    print("\nTest 1: Same subnet communication (Client1 -> Client2)")
    print("Sending a message from Client1 to Client2...")
    print("Route trace will show direct communication within subnet:")
    # Reduced from 5 messages to 1
    net.send_message("Client1", "Hello Client2!", target_ip="192.168.1.102")
    time.sleep(0.2)
    
    print("\nTest 2: Cross-subnet communication (Client1 -> Workstation1)")
    print("Sending a message from Client1 to Workstation1...")
    print("Route trace will show packets going through the router:")
    # Reduced from 5 messages to 1
    net.send_message("Client1", "Hello Workstation1!", target_ip="192.168.2.101")
    time.sleep(0.2)
    
    print("\nTest 3: Local subnet broadcast from Server")
    print("Broadcasting a message:")
    # Reduced from 2 messages to 1
    net.send_message("Server", "Broadcast message from server", target_ip="192.168.1.255")
    time.sleep(0.2)
    
    print("\nTest 4: Cross-subnet messages with route analysis")
    print("Sending a message between Workstation2 and Server...")
    print("Observe the route through the router's interfaces:")
    # Reduced from 3 messages to 1
    net.send_message("Workstation2", "Testing routing", target_ip="192.168.1.100")
    time.sleep(0.2)
    
    print("\nTest 5: Route lookup and path analysis")
    router = net.routers["MainRouter"]
    test_ips = [
        "192.168.1.100",
        "192.168.2.101",
        "192.168.3.1",
        "10.0.0.1"
    ]
    
    for ip in test_ips:
        route = router.routing_table.lookup(ip)
        if route:
            print(f"Route found for {ip}: {route}")
            print(f"Packet would traverse: Source -> MainRouter({route.interface}) -> {ip}")
        else:
            print(f"No route found for {ip}")
    
    print("\n=== Test Case Execution Complete ===")
    return net


def run_advanced_network_test():
    """Run advanced network test with reduced waiting times"""
    print("\n=== Advanced Network Layer Test Case ===")
    print("Creating a network with multiple subnets and routers...")
    print(f"Test will terminate after {Network.MAX_PACKETS} packets/frames")
    
    # Create the network
    net = Network("AdvancedTestNetwork")
    
    # Create devices in subnet 1 (192.168.1.0/24)
    print("\nCreating devices in subnet 192.168.1.0/24...")
    server1 = net.add_device("Server1", "192.168.1.100", "255.255.255.0", "192.168.1.1")
    client1 = net.add_device("Client1", "192.168.1.101", "255.255.255.0", "192.168.1.1")
    
    # Create devices in subnet 2 (192.168.2.0/24)
    print("\nCreating devices in subnet 192.168.2.0/24...")
    server2 = net.add_device("Server2", "192.168.2.100", "255.255.255.0", "192.168.2.1")
    client2 = net.add_device("Client2", "192.168.2.101", "255.255.255.0", "192.168.2.1")
    
    # Create devices in subnet 3 (192.168.3.0/24)
    print("\nCreating devices in subnet 192.168.3.0/24...")
    server3 = net.add_device("Server3", "192.168.3.100", "255.255.255.0", "192.168.3.1")
    client3 = net.add_device("Client3", "192.168.3.101", "255.255.255.0", "192.168.3.1")
    
    # Create routers
    print("\nCreating and configuring routers...")
    router1 = net.add_router("Router1")
    router2 = net.add_router("Router2")
    router3 = net.add_router("Router3")
    
    # Configure Router1
    net.configure_router("Router1", [
        {
            "name": "eth0",
            "ip_address": "192.168.1.1",
            "subnet_mask": "255.255.255.0",
            "routes": [
                {
                    "destination": "192.168.1.0",
                    "next_hop": "0.0.0.0",
                    "subnet_mask": "255.255.255.0"
                }
            ]
        },
        {
            "name": "eth1",
            "ip_address": "10.0.0.1",
            "subnet_mask": "255.255.255.252",
            "routes": [
                {
                    "destination": "10.0.0.0",
                    "next_hop": "0.0.0.0",
                    "subnet_mask": "255.255.255.252"
                }
            ]
        }
    ])
    
    # Configure Router2
    net.configure_router("Router2", [
        {
            "name": "eth0",
            "ip_address": "192.168.2.1",
            "subnet_mask": "255.255.255.0",
            "routes": [
                {
                    "destination": "192.168.2.0",
                    "next_hop": "0.0.0.0",
                    "subnet_mask": "255.255.255.0"
                }
            ]
        },
        {
            "name": "eth1",
            "ip_address": "10.0.0.2",
            "subnet_mask": "255.255.255.252",
            "routes": [
                {
                    "destination": "10.0.0.0",
                    "next_hop": "0.0.0.0",
                    "subnet_mask": "255.255.255.252"
                }
            ]
        },
        {
            "name": "eth2",
            "ip_address": "10.0.0.5",
            "subnet_mask": "255.255.255.252",
            "routes": [
                {
                    "destination": "10.0.0.4",
                    "next_hop": "0.0.0.0",
                    "subnet_mask": "255.255.255.252"
                }
            ]
        }
    ])
    
    # Configure Router3
    net.configure_router("Router3", [
        {
            "name": "eth0",
            "ip_address": "192.168.3.1",
            "subnet_mask": "255.255.255.0",
            "routes": [
                {
                    "destination": "192.168.3.0",
                    "next_hop": "0.0.0.0",
                    "subnet_mask": "255.255.255.0"
                }
            ]
        },
        {
            "name": "eth1",
            "ip_address": "10.0.0.6",
            "subnet_mask": "255.255.255.252",
            "routes": [
                {
                    "destination": "10.0.0.4",
                    "next_hop": "0.0.0.0",
                    "subnet_mask": "255.255.255.252"
                }
            ]
        }
    ])
    
    # Create network links
    print("\nCreating network links...")
    # Subnet 1 links
    net.add_link("Link1_1", "Server1", "Router1")
    net.add_link("Link1_2", "Client1", "Router1")
    
    # Subnet 2 links
    net.add_link("Link2_1", "Server2", "Router2")
    net.add_link("Link2_2", "Client2", "Router2")
    
    # Subnet 3 links
    net.add_link("Link3_1", "Server3", "Router3")
    net.add_link("Link3_2", "Client3", "Router3")
    
    # Router interconnection links
    net.add_link("Link_R1_R2", "Router1", "Router2")  # 10.0.0.0/30
    net.add_link("Link_R2_R3", "Router2", "Router3")  # 10.0.0.4/30
    
    # Enable RIP on all routers
    print("\nEnabling RIP routing protocol on all routers...")
    router1.enable_rip()
    router2.enable_rip()
    router3.enable_rip()
    
    # Add static routes for initial connectivity
    print("\nAdding static routes...")
    # Router1 static routes
    router1.add_route("192.168.2.0", "10.0.0.2", "255.255.255.0", "eth1", 2)
    router1.add_route("192.168.3.0", "10.0.0.2", "255.255.255.0", "eth1", 3)
    
    # Router2 static routes
    router2.add_route("192.168.1.0", "10.0.0.1", "255.255.255.0", "eth1", 2)
    router2.add_route("192.168.3.0", "10.0.0.6", "255.255.255.0", "eth2", 2)
    
    # Router3 static routes
    router3.add_route("192.168.1.0", "10.0.0.5", "255.255.255.0", "eth1", 3)
    router3.add_route("192.168.2.0", "10.0.0.5", "255.255.255.0", "eth1", 2)
    
    # Display the network topology
    print("\nNetwork topology:")
    net.display_network()
    
    # Test cases
    print("\n=== Running Advanced Test Cases ===")
    
    # Test 1: ARP Resolution
    print("\nTest 1: ARP Resolution")
    if net.packet_count < net.MAX_PACKETS:
        print("Client1 sending message to Server1 (same subnet, requires ARP)...")
        net.send_message("Client1", "Hello Server1! This is a same-subnet ARP test.", target_ip="192.168.1.100")
    
    # Test 2: Cross-subnet routing with multiple hops
    print("\nTest 2: Cross-subnet routing (Client1 -> Server3)")
    if net.packet_count < net.MAX_PACKETS:
        print("Sending message from Client1 to Server3 (requires routing through all routers)...")
        net.send_message("Client1", "Hello Server3! This is a cross-network routing test.", target_ip="192.168.3.100")
    
    # Test 3: RIP Protocol Updates
    print("\nTest 3: RIP Protocol Updates")
    if net.packet_count < net.MAX_PACKETS:
        print("Waiting for RIP updates to propagate (5 seconds)...")
        time.sleep(5)  # Reduced from 30 seconds
        
        # Display updated routing tables
        print("\nRouting tables after RIP updates:")
        for router_name in ["Router1", "Router2", "Router3"]:
            router = net.routers[router_name]
            print(f"\n{router_name} Routing Table:")
            for route in router.routing_table.routes:
                print(f"  {route}")
    
    # Test 4: Link failure simulation
    print("\nTest 4: Link Failure Simulation")
    if net.packet_count < net.MAX_PACKETS:
        print("Simulating failure of direct link between Router2 and Router3...")
        # Remove the link
        net.remove_link("Link_R2_R3")
        
        # Wait for RIP to converge
        print("Waiting for RIP to converge after link failure (5 seconds)...")
        time.sleep(5)  # Reduced from 30 seconds
        
        # Test alternate path
        print("\nTesting alternate path from Client2 to Server3...")
        net.send_message("Client2", "Hello Server3! This is a post-failure routing test.", target_ip="192.168.3.100")
    
    print(f"\nTest completed. Total packets/frames transmitted: {net.packet_count}")
    return net

# Add enable_go_back_n method to Network class
def enable_go_back_n(self, device_name, window_size=4):
    """Enable Go-Back-N protocol for a device with specified window size"""
    device = (self.devices.get(device_name) or 
              self.hubs.get(device_name) or 
              self.bridges.get(device_name) or 
              self.switches.get(device_name) or
              self.routers.get(device_name))
    
    if not device:
        self.logger.error(f"Device '{device_name}' not found")
        return False
    
    # Set Go-Back-N properties
    device.use_go_back_n = True
    device.window_size = window_size
    self.logger.info(f"Enabled Go-Back-N for {device_name} with window size {window_size}")
    return True

Network.enable_go_back_n = enable_go_back_n

def simplified_networking_demo():
    """Run a simplified demonstration of basic networking concepts"""
    print("\n=== Basic Networking Demonstration ===")
    print("This demonstration will show how devices communicate through IP networks")
    
    net = Network("SimpleDemoNetwork")
    
    # Create simple topology with two subnets
    print("\nCreating a simple network with two subnets (192.168.1.0/24 and 192.168.2.0/24)")
    
    # Create devices
    net.add_device("PC1", "192.168.1.10", "255.255.255.0", "192.168.1.1")
    net.add_device("PC2", "192.168.1.11", "255.255.255.0", "192.168.1.1")
    net.add_device("Server1", "192.168.2.10", "255.255.255.0", "192.168.2.1")
    
    # Create router
    router = net.add_router("Router1")
    
    # Configure router interfaces
    net.configure_router("Router1", [
        {
            "name": "eth0",
            "ip_address": "192.168.1.1",
            "subnet_mask": "255.255.255.0",
            "routes": [
                {
                    "destination": "192.168.1.0",
                    "next_hop": "0.0.0.0",
                    "subnet_mask": "255.255.255.0"
                }
            ]
        },
        {
            "name": "eth1",
            "ip_address": "192.168.2.1",
            "subnet_mask": "255.255.255.0",
            "routes": [
                {
                    "destination": "192.168.2.0",
                    "next_hop": "0.0.0.0",
                    "subnet_mask": "255.255.255.0"
                }
            ]
        }
    ])
    
    # Connect everything
    net.add_link("Link1", "PC1", "Router1")
    net.add_link("Link2", "PC2", "Router1")
    net.add_link("Link3", "Server1", "Router1")
    
    # Display the network
    net.display_network()
    
    # Run simple tests with shorter messages
    print("\nTest 1: Local communication (PC1 -> PC2)")
    print("This demonstrates Layer 2 (MAC addressing) and ARP for local delivery")
    net.send_message("PC1", "Hello PC2!", target_ip="192.168.1.11")
    time.sleep(0.5)  # Small delay
    
    print("\nTest 2: Cross-subnet communication (PC1 -> Server1)")
    print("This demonstrates Layer 3 (IP routing) through the router")
    net.send_message("PC1", "Hello Server1!", target_ip="192.168.2.10")
    time.sleep(0.5)  # Small delay
    
    return net

def layer_demonstrations():
    """Run focused demonstrations for each network layer"""
    while True:
        print("\n=== Network Layer Demonstrations ===")
        print("1. Physical Layer: CSMA/CD Demo (Media Access Control)")
        print("2. Data Link Layer: Error Control Demo")
        print("3. Network Layer: Routing & IP Demo")
        print("4. Return to Main Menu")
        
        choice = input("\nSelect a demonstration (1-4): ").strip()
        
        if choice == "1":
            print("\nRunning CSMA/CD Demonstration (Physical Layer)...")
            print("This demonstrates how devices share a physical medium and handle collisions")
            demonstrate_csma_cd()
        elif choice == "2":
            print("\nRunning Error Control Demonstration (Data Link Layer)...")
            print("This demonstrates how devices detect and recover from transmission errors")
            demonstrate_error_control()
        elif choice == "3":
            print("\nRunning IP Routing Demonstration (Network Layer)...")
            print("This demonstrates how packets are routed between different networks")
            demonstrate_ip_networking()
        elif choice == "4":
            print("Returning to main menu...")
            break
        else:
            print("Invalid selection. Please try again.")

def test_cases_menu():
    """Present a menu of test cases to run"""
    while True:
        print("\n=== Network Test Cases ===")
        print("1. Basic Network Test (Simple two-subnet scenario)")
        print("2. Advanced Network Test (Multi-router scenario with RIP)")
        print("3. Simple Network Demo (Quick overview of all layers)")
        print("4. Return to Main Menu")
        
        choice = input("\nSelect a test case (1-4): ").strip()
        
        if choice == "1":
            print("\nRunning Basic Network Test...")
            print("This test demonstrates routing between two subnets")
            network = run_network_test()
            print("Basic test completed.")
        elif choice == "2":
            print("\nRunning Advanced Network Test...")
            print("This test demonstrates dynamic routing with RIP protocol")
            network = run_advanced_network_test()
            print("Advanced test completed.")
        elif choice == "3":
            print("\nRunning Simple Network Demo...")
            network = simplified_networking_demo()
            print("Simple network demo completed.")
        elif choice == "4":
            print("Returning to main menu...")
            break
        else:
            print("Invalid selection. Please try again.")

if __name__ == "__main__":
    # Start with a simplified menu interface
    print("\n=== TCP/IP Network Simulator ===")
    print("This simulator demonstrates networking concepts across multiple layers")
    
    # Create a default network
    network = Network("MainNetwork")
    
    while True:
        print("\n=== Main Menu ===")
        print("1. Run Test Cases")
        print("2. Layer-specific Demonstrations")
        print("3. Interactive Command Line")
        print("4. Exit Simulator")
        
        choice = input("\nSelect an option (1-4): ").strip()
        
        if choice == "1":
            test_cases_menu()
        elif choice == "2":
            layer_demonstrations()
        elif choice == "3":
            print("\nStarting interactive command line. Type 'help' for commands.")
            interactive_cli()
        elif choice == "4":
            print("Exiting simulator...")
            break
        else:
            print("Invalid selection. Please try again.")
