"""
Device implementation for the TCP/IP Network Simulator.
"""

import time
import threading
import random
from TCP_IP.utils.logging_config import setup_logger
from TCP_IP.datalink.mac_address import MACAddress
from TCP_IP.datalink.frame import Frame, FrameType
from TCP_IP.config import TRANSMISSION_DELAY, BIT_ERROR_RATE
from TCP_IP.network.ip_address import IPAddress
from TCP_IP.network.packet import Packet

class Device:
    """Base class for all network devices."""
    
    def __init__(self, name):
        self.name = name
        self.mac_address = MACAddress()
        self.connections = []  # List of links connected to this device
        self.received_messages = []  # Messages received by this device
        self.logger = setup_logger(f"{self.name}", f"{self.name}")
        self.logger.info(f"Device {self.name} created with MAC {self.mac_address}")
        
        # Network Layer properties
        self.ip_address = None # Add IP address attribute
        self.arp_table = {} # IP Address (str) -> MAC Address (str)
        
        # Data Link Layer properties
        self.next_sequence_number = 0
        self.expected_sequence_number = 0
        self.window_size = 4  # Window size for sliding window protocol
        self.timeout = 1.0  # Timeout in seconds for retransmission
        self.unacknowledged_frames = {}  # sequence_number -> (frame, timestamp)
        self.buffer = {}  # Buffer for received out-of-order frames per source MAC
        self.use_go_back_n = False  # Default to Stop-and-Wait
        
        # Add default gateway attribute
        self.default_gateway = None
    
    def connect(self, link):
        """Connect this device to a link."""
        self.connections.append(link)
        self.logger.info(f"Connected to link {link.name}")
    
    def disconnect(self, link):
        """Disconnect this device from a link."""
        if link in self.connections:
            self.connections.remove(link)
            self.logger.info(f"Disconnected from link {link.name}")
    
    def send_message(self, message, target_mac=None):
        """Send a message through all connected links."""
        if not self.connections:
            self.logger.error(f"Cannot send message: No connections available")
            return False
        
        self.logger.info(f"Sending message: {message}")
        
        # Create frames from the message
        frames = self._create_frames(message, target_mac)
        
        # Send using the configured protocol
        if self.use_go_back_n:
            success = self._send_go_back_n(frames)
        else:
            success = self._send_stop_and_wait(frames)
        
        return success
    
    def _create_frames(self, message, target_mac):
        """Split a message into frames, one character per frame with size information"""
        frames = []
        # If target_mac is None, use broadcast address
        dest_mac = target_mac if target_mac else "FF:FF:FF:FF:FF:FF"
        
        # Create a special first frame with total message size
        size_frame = Frame(
            str(self.mac_address), 
            dest_mac, 
            f"__SIZE__{len(message)}", 
            self.next_sequence_number,
            frame_type=FrameType.DATA
        )
        frames.append(size_frame)
        self.next_sequence_number += 1
        
        # Create a frame for each character in the message
        for i, char in enumerate(message):
            frame = Frame(str(self.mac_address), dest_mac, char, self.next_sequence_number)
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
                if frame.frame_type == FrameType.DATA:
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
                                str(self.mac_address),
                                frame.source_mac,
                                f"ACK-{next_expected}",  # ACK for next expected frame
                                next_expected - 1,  # Use the current frame's sequence number
                                FrameType.ACK
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
                                str(self.mac_address),
                                frame.source_mac,
                                f"ACK-{next_expected}",  # ACK for next expected frame
                                frame.sequence_number,  # Use the current frame's sequence number
                                FrameType.ACK
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
                                self.buffer[frame.source_mac].append(frame)
                                self.logger.info(f"Buffered frame {frame.sequence_number}")
                            
                            # Send ACK for the next expected frame (duplicate ACK)
                            # This tells the sender to retransmit from this point
                            ack_frame = Frame(
                                str(self.mac_address),
                                frame.source_mac,
                                f"ACK-{self.expected_sequence_number}",  # Request the expected frame
                                self.expected_sequence_number-1,
                                FrameType.ACK
                            )
                            self.logger.info(f"Sending duplicate ACK {self.expected_sequence_number} (still expecting frame {self.expected_sequence_number})")
                            for link in self.connections:
                                link.transmit(ack_frame, self)
                
                elif frame.frame_type == FrameType.ACK:
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
                
                elif frame.frame_type == FrameType.NAK:
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
                if frame.frame_type == FrameType.DATA:
                    # Send duplicate ACK for the last correctly received frame
                    ack_frame = Frame(
                        str(self.mac_address),
                        frame.source_mac,
                        f"ACK-{self.expected_sequence_number}",  # Request the expected frame
                        self.expected_sequence_number-1,
                        FrameType.ACK
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
        for source_mac, frames in self.buffer.items():
            frames.sort(key=lambda f: f.sequence_number)
            
            # Process frames that are now in order
            while frames and frames[0].sequence_number == self.expected_sequence_number:
                frame = frames.pop(0)
                self.logger.info(f"Processing buffered frame {frame.sequence_number}")
                self.received_messages.append((frame.data, str(source_mac)))
                self.expected_sequence_number += 1
    
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
        """Reassemble a complete message from buffered characters"""
        if not hasattr(self, 'char_buffers') or source_mac not in self.char_buffers:
            self.logger.warning(f"No character buffer found for {source_mac}")
            return
        
        # Get the character buffer for this source
        char_buffer = self.char_buffers[source_mac]
        
        # Check if we have all characters
        if len(char_buffer) >= total_size:
            # Sort by sequence number and join characters
            # Skip the first frame (size frame) by filtering sequence numbers
            # that are greater than the size frame's sequence number
            size_frame_seq = min(char_buffer.keys()) - 1  # Estimate the size frame's sequence number
            sorted_chars = [char_buffer[seq] for seq in sorted(char_buffer.keys()) if seq > size_frame_seq]
            
            # Take only the first 'total_size' characters
            sorted_chars = sorted_chars[:total_size]
            message = ''.join(sorted_chars)
            
            self.logger.info(f"Reassembled message from {source_mac}: '{message}'")
            self.received_messages.append((message, source_mac))
            
            # Clear the buffer for this source
            self.char_buffers[source_mac] = {}
            
            # Clear the expected message size
            if hasattr(self, 'expected_message_sizes') and source_mac in self.expected_message_sizes:
                del self.expected_message_sizes[source_mac]
        else:
            self.logger.warning(f"Incomplete message from {source_mac}: have {len(char_buffer)} of {total_size} characters")
    
    def assign_ip_address(self, ip_address_str, subnet_mask_str="255.255.255.0"):
        """Assign an IP address and subnet mask to the device."""
        try:
            self.ip_address = IPAddress(ip_address_str, subnet_mask_str)
            self.logger.info(f"Assigned IP address {self.ip_address} to {self.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to assign IP address {ip_address_str}/{subnet_mask_str}: {e}")
            return False

    def __str__(self):
        return f"Device({self.name}, MAC={self.mac_address})"

    # New method to process received packets (Network Layer)
    def process_packet(self, packet, source_device):
        """Process a received network layer packet."""
        self.logger.info(f"Received packet from {packet.source_ip} to {packet.destination_ip} on {self.name}")

        # Check if the packet is for this device
        if self.ip_address and packet.destination_ip == self.ip_address.address:
            self.logger.info(f"Packet for me! Data: {packet.data}")
            # Pass data up to the next layer (Transport Layer - not implemented yet)
            self.received_messages.append((packet.data, packet.source_ip)) # Store for now
        else:
            self.logger.info(f"Packet not for me, needs routing.")
            # If this is a router, forward the packet
            if isinstance(self, Router): # Need to import Router
                 self.forward_packet(packet, source_device) # Router's forwarding logic
            else:
                 self.logger.warning(f"Device {self.name} received packet not for it, but is not a router. Dropping.")

    # Add default gateway attribute
    def set_default_gateway(self, gateway_ip_str):
        """Set the default gateway IP address."""
        self.default_gateway = IPAddress(gateway_ip_str)
        self.logger.info(f"Set default gateway for {self.name} to {self.default_gateway.address}")

    # New method to send a packet (Network Layer initiation)
    def send_packet(self, destination_ip_str, data, protocol=0):
        """Create and send a network layer packet."""
        if not self.ip_address:
            self.logger.error(f"{self.name} cannot send packet: No IP address assigned.")
            return False

        packet = Packet(self.ip_address.address, destination_ip_str, data, protocol=protocol)
        self.logger.info(f"{self.name} created packet: {packet}")

        # Determine the next hop IP
        next_hop_ip_str = None
        # Check if destination is on the local network
        try:
            dest_ip_obj = IPAddress(destination_ip_str)
            if self.ip_address.is_in_network(dest_ip_obj):
                self.logger.info(f"Destination {destination_ip_str} is on local network.")
                next_hop_ip_str = destination_ip_str
            elif self.default_gateway:
                self.logger.info(f"Destination {destination_ip_str} is remote, using default gateway {self.default_gateway.address}.")
                next_hop_ip_str = self.default_gateway.address
            else:
                self.logger.error(f"{self.name} cannot send packet to {destination_ip_str}: No default gateway configured for remote networks.")
                return False
        except Exception as e:
             self.logger.error(f"Error determining next hop for {destination_ip_str}: {e}")
             return False


        # Perform ARP lookup for the next hop IP
        next_hop_mac = self.arp_lookup(next_hop_ip_str)

        if next_hop_mac:
            self.logger.info(f"Next hop IP {next_hop_ip_str} resolved to MAC {next_hop_mac}")
            # Encapsulate the packet in a Data Link frame
            # Source MAC is this device's MAC
            # Destination MAC is the next hop's MAC (from ARP)
            frame = Frame(
                str(self.mac_address),
                next_hop_mac,
                packet, # The packet is the data payload
                sequence_number=self.next_sequence_number, # Use Data Link seq number
                frame_type=FrameType.DATA
            )
            self.next_sequence_number += 1 # Increment Data Link seq number

            # Send the frame out all connected links (simplified for now, assumes one relevant link)
            # In a real scenario, a device would send out the interface connected to the next hop.
            # For this simulator, if connected to a switch/hub, it goes there.
            if self.connections:
                 self.logger.info(f"{self.name} sending frame out connected links.")
                 # Need to select the correct interface/link if multiple exist
                 # For simplicity, let's assume one connection or broadcast on all
                 for link in self.connections:
                     link.transmit(frame, self)
                 return True
            else:
                 self.logger.error(f"{self.name} has no connections to send frame.")
                 return False

        else:
            self.logger.warning(f"ARP lookup failed for {next_hop_ip_str}. Cannot send packet.")
            # TODO: Queue packet and wait for ARP reply

            return False


    # Implement ARP lookup for a device (host)
    def arp_lookup(self, target_ip_str):
        """Lookup MAC address for target_ip_str in ARP table. If not found, initiate ARP request."""
        if target_ip_str in self.arp_table:
            self.logger.debug(f"ARP hit for {target_ip_str}: {self.arp_table[target_ip_str]}")
            return self.arp_table[target_ip_str]
        else:
            self.logger.info(f"ARP miss for {target_ip_str}. Initiating ARP request.")
            self.send_arp_request(target_ip_str) # Need to implement send_arp_request
            # In a real simulator, you'd queue the packet and wait for a reply.
            # For now, return None, the sending logic handles the drop/queue.
            return None

    # Implement ARP request handling for a device (host)
    def handle_arp_request(self, frame, receiving_link):
        """Handle incoming ARP request."""
        # Assuming ARP request data format is "ARP_REQUEST:<sender_ip>:<sender_mac>:<target_ip>"
        try:
            parts = frame.data.split(':')
            if len(parts) == 4 and parts[0] == "ARP_REQUEST":
                sender_ip = parts[1]
                sender_mac = parts[2]
                target_ip = parts[3]

                self.logger.info(f"{self.name} received ARP request for {target_ip} from {sender_ip} ({sender_mac})")

                # Add sender to ARP table
                self.arp_table[sender_ip] = sender_mac
                self.logger.debug(f"Added {sender_ip} -> {sender_mac} to ARP table.")

                # If the target IP is this device's IP, send a reply
                if self.ip_address and target_ip == self.ip_address.address:
                    self.logger.info(f"ARP request is for me! Sending ARP reply to {sender_ip}")
                    self.send_arp_reply(sender_ip, sender_mac, frame.source_mac, receiving_link) # Need to implement send_arp_reply
            else:
                self.logger.warning(f"Received malformed ARP request frame data: {frame.data}")
        except Exception as e:
            self.logger.error(f"Error processing ARP request: {e}")


    # Implement ARP reply handling for a device (host)
    def handle_arp_reply(self, frame, receiving_link):
        """Handle incoming ARP reply."""
        # Assuming ARP reply data format is "ARP_REPLY:<sender_ip>:<sender_mac>:<target_ip>"
        try:
            parts = frame.data.split(':')
            if len(parts) == 4 and parts[0] == "ARP_REPLY":
                sender_ip = parts[1]
                sender_mac = parts[2]
                target_ip = parts[3] # This should be our IP

                self.logger.info(f"{self.name} received ARP reply from {sender_ip} ({sender_mac})")

                # Add sender to ARP table
                self.arp_table[sender_ip] = sender_mac
                self.logger.debug(f"Added {sender_ip} -> {sender_mac} to ARP table.")

                # TODO: Check if there are queued packets for this IP and send them

            else:
                self.logger.warning(f"Received malformed ARP reply frame data: {frame.data}")
        except Exception as e:
            self.logger.error(f"Error processing ARP reply: {e}")


    # Implement sending ARP request for a device (host)
    def send_arp_request(self, target_ip_str):
        """Send an ARP request for target_ip_str."""
        if not self.ip_address:
            self.logger.error(f"{self.name} cannot send ARP request: No IP address assigned.")
            return

        # ARP request is broadcast at the Data Link layer
        arp_frame_data = f"ARP_REQUEST:{self.ip_address.address}:{self.mac_address}:{target_ip_str}"
        arp_frame = Frame(
            str(self.mac_address),
            "FF:FF:FF:FF:FF:FF", # Broadcast MAC address
            arp_frame_data,
            sequence_number=0, # ARP frames don't need sequence numbers for this sim
            frame_type=FrameType.ARP_REQUEST
        )

        self.logger.info(f"{self.name} sending ARP request for {target_ip_str}")
        # Send out all connected links (assuming they are on the same broadcast domain)
        for link in self.connections:
            link.transmit(arp_frame, self)

    # Implement sending ARP reply for a device (host)
    def send_arp_reply(self, target_ip_str, target_mac_str, destination_mac_str, source_link):
        """Send an ARP reply to target_ip_str (who sent the request)."""
        if not self.ip_address:
            self.logger.error(f"{self.name} cannot send ARP reply: No IP address assigned.")
            return

        # ARP reply is unicast to the requester's MAC address
        arp_frame_data = f"ARP_REPLY:{self.ip_address.address}:{self.mac_address}:{target_ip_str}"
        arp_frame = Frame(
            str(self.mac_address),
            destination_mac_str, # Send directly back to the requester's MAC
            arp_frame_data,
            sequence_number=0,
            frame_type=FrameType.ARP_REPLY
        )

        self.logger.info(f"{self.name} sending ARP reply to {target_ip_str} ({destination_mac_str})")
        # Send out the link where the request was received
        source_link.transmit(arp_frame, self)
