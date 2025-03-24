"""
TCP/IP Network Simulator
A modular simulator focusing on the Physical and Data Link Layers with extensibility for higher layers.
"""

import uuid
import random
import time
import logging
import os
import threading
from enum import Enum

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Setup logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Constants
MAX_FRAME_SIZE = 1024  # Maximum size of a frame in bytes
TRANSMISSION_DELAY = 0.01  # Simulated delay for transmission in seconds
BIT_ERROR_RATE = 0.01  # Probability of bit error in transmission
CSMA_CD_MAX_ATTEMPTS = 16  # Maximum attempts before giving up
CSMA_CD_SLOT_TIME = 0.02  # Time slot for backoff in seconds
MEDIUM_BUSY_PROBABILITY = 0.3  # Probability that medium is initially busy
MEDIUM_BUSY_DURATION = 0.1  # How long the medium stays busy in seconds
ERROR_INJECTION_RATE = 0.2  # 20% chance of introducing an error in a frame
BUSY_TIME_RANGE = (0.05, 0.2)  # Range of time (in seconds) that the medium stays busy

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


class Frame:
    """Represents a data frame at the Data Link Layer"""
    
    def __init__(self, source_mac, destination_mac, data, sequence_number=0, frame_type=FrameType.DATA):
        self.source_mac = source_mac
        self.destination_mac = destination_mac
        self.data = data
        self.sequence_number = sequence_number
        self.frame_type = frame_type
        self.checksum = self._calculate_checksum()
        self.timestamp = time.time()  # For timeout calculations
    
    def _calculate_checksum(self):
        """Calculate a simple checksum for error detection"""
        # Use a simple sum of bytes as checksum for demonstration
        checksum = 0
        # Include header fields in checksum
        for c in str(self.source_mac) + str(self.destination_mac) + str(self.sequence_number):
            checksum = (checksum + ord(c)) % 256
        # Include data in checksum
        for c in self.data:
            checksum = (checksum + ord(c)) % 256
        return checksum
    
    def is_valid(self):
        """Check if the frame has a valid checksum"""
        return self._calculate_checksum() == self.checksum
    
    def introduce_error(self):
        """Introduce a random bit error in the frame data for testing"""
        if len(self.data) > 0:
            char_pos = random.randint(0, len(self.data) - 1)
            char_list = list(self.data)
            # Flip a random bit in the selected character
            char_code = ord(char_list[char_pos])
            bit_pos = random.randint(0, 7)
            char_code ^= (1 << bit_pos)  # Flip the bit
            char_list[char_pos] = chr(char_code)
            self.data = ''.join(char_list)
            # Don't update checksum to simulate error
    
    def create_ack(self):
        """Create an acknowledgment frame for this frame"""
        return Frame(
            self.destination_mac,
            self.source_mac,
            f"ACK-{self.sequence_number}",
            self.sequence_number,
            FrameType.ACK
        )
    
    def create_nak(self):
        """Create a negative acknowledgment frame for this frame"""
        return Frame(
            self.destination_mac,
            self.source_mac,
            f"NAK-{self.sequence_number}",
            self.sequence_number,
            FrameType.NAK
        )
    
    def __str__(self):
        type_str = self.frame_type.name
        if len(self.data) > 20:
            data_preview = self.data[:20] + "..."
        else:
            data_preview = self.data
        return f"Frame[{type_str}:{self.sequence_number}] {self.source_mac[:6]}...-->{self.destination_mac[:6]}...: {data_preview}"


class Device:
    """Base class for all network devices."""
    
    def __init__(self, name):
        self.name = name
        self.mac_address = MACAddress()
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
    
    def send_message(self, message, target_mac=None):
        """Send a message through all connected links."""
        if not self.connections:
            self.logger.error(f"Cannot send message: No connections available")
            return False
        
        self.logger.info(f"Sending message: {message}")
        
        # Create frames from the message
        frames = self._create_frames(message, target_mac)
        
        # Send using the configured protocol
        if hasattr(self, 'use_go_back_n') and self.use_go_back_n:
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
                                self.buffer.append(frame)
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
            frame.source_mac,
            frame.destination_mac,
            frame.data,
            frame.sequence_number,
            frame.frame_type
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
            if random.random() < ERROR_INJECTION_RATE and frame.frame_type == FrameType.DATA:
                self.logger.warning(f"Error introduced in frame {frame.sequence_number}")
                # Introduce error
                transmitted_frame.introduce_error()
            
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
    """Manages the network topology and message flow."""
    
    def __init__(self, name):
        self.name = name
        self.devices = {}  # name -> Device
        self.hubs = {}     # name -> Hub
        self.bridges = {}  # name -> Bridge
        self.switches = {} # name -> Switch
        self.links = {}    # name -> Link
        self.logger = logging.getLogger(f"Network_{name}")
        file_handler = logging.FileHandler(f"logs/network_{name}.log")
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
    
    def add_device(self, name):
        """Add a new device to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        device = Device(name)
        self.devices[name] = device
        self.logger.info(f"Added device: {name}")
        return device
    
    def add_hub(self, name):
        """Add a new hub to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        hub = Hub(name)
        self.hubs[name] = hub
        self.logger.info(f"Added hub: {name}")
        return hub
    
    def add_bridge(self, name):
        """Add a new bridge to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        bridge = Bridge(name)
        self.bridges[name] = bridge
        self.logger.info(f"Added bridge: {name}")
        return bridge
    
    def add_switch(self, name):
        """Add a new switch to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        switch = Switch(name)
        self.switches[name] = switch
        self.logger.info(f"Added switch: {name}")
        return switch
    
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
                         self.switches.get(endpoint1_name))
            if not endpoint1:
                self.logger.error(f"Endpoint '{endpoint1_name}' not found")
                return None
        
        if endpoint2_name:
            endpoint2 = (self.devices.get(endpoint2_name) or 
                         self.hubs.get(endpoint2_name) or 
                         self.bridges.get(endpoint2_name) or 
                         self.switches.get(endpoint2_name))
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
    
    def send_message(self, source_name, message, target_name=None):
        """Send a message from a source device to a target device."""
        source = (self.devices.get(source_name) or 
                  self.hubs.get(source_name) or 
                  self.bridges.get(source_name) or 
                  self.switches.get(source_name))
        
        if not source:
            self.logger.error(f"Source device '{source_name}' not found")
            return False
        
        target = None
        target_mac = None
        
        if target_name:
            target = (self.devices.get(target_name) or 
                      self.hubs.get(target_name) or 
                      self.bridges.get(target_name) or 
                      self.switches.get(target_name))
            
            if not target:
                self.logger.error(f"Target device '{target_name}' not found")
                return False
            
            target_mac = str(target.mac_address)
        
        return source.send_message(message, target_mac)
    
    def display_network(self):
        """Display the current network topology."""
        print(f"\n=== Network: {self.name} ===")
        
        print("\nDevices:")
        for name, device in self.devices.items():
            print(f"  {name} (MAC: {device.mac_address})")
        
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
        return (f"Network({self.name}, {len(self.devices)} devices, {len(self.hubs)} hubs, "
                f"{len(self.bridges)} bridges, {len(self.switches)} switches, {len(self.links)} links)")


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
            print("  add device <name>           - Add a new device")
            print("  add hub <name>              - Add a new hub")
            print("  add bridge <name>           - Add a new bridge")
            print("  add switch <name>           - Add a new switch")
            print("  add link <name> [dev1] [dev2] - Add a new link between devices")
            print("  remove device <name>        - Remove a device")
            print("  remove hub <name>           - Remove a hub")
            print("  remove bridge <name>        - Remove a bridge")
            print("  remove switch <name>        - Remove a switch")
            print("  remove link <name>          - Remove a link")
            print("  connect <link> <endpoint>   - Connect an endpoint to a link")
            print("  disconnect <link> <endpoint> - Disconnect an endpoint from a link")
            print("  send <source> <message> [target] - Send a message")
            print("  display                     - Display network topology")
            print("  demo error                   - Demonstrate error control")
            print("  demo csmacd                  - Demonstrate CSMA/CD protocol")
            print("  help                        - Show this help message")
            print("  exit/quit                   - Exit the simulator")
        
        elif parts[0] == "add":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            if parts[1] == "device":
                network.add_device(parts[2])
            
            elif parts[1] == "hub":
                network.add_hub(parts[2])
            
            elif parts[1] == "bridge":
                network.add_bridge(parts[2])
            
            elif parts[1] == "switch":
                network.add_switch(parts[2])
            
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
                        network.switches.get(endpoint_name))
            
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
                        network.switches.get(endpoint_name))
            
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
            
            network.send_message(source_name, message, target_name)
        
        elif parts[0] == "display":
            network.display_network()
        
        elif parts[0] == "demo" and parts[1] == "error":
            demonstrate_error_control()
        
        elif parts[0] == "demo" and parts[1] == "csmacd":
            demonstrate_csma_cd()
        
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
    pc3 = network.add_device("PC3")
    pc4 = network.add_device("PC4")
    
    # Create a hub to simulate a shared medium
    hub = network.add_hub("Hub1")
    
    # Connect all devices to the hub
    link1 = network.add_link("Link1", "PC1", "Hub1")
    link2 = network.add_link("Link2", "PC2", "Hub1")
    link3 = network.add_link("Link3", "PC3", "Hub1")
    link4 = network.add_link("Link4", "PC4", "Hub1")
    
    # Display the network
    network.display_network()
    
    # Simulate concurrent transmissions to demonstrate collision detection
    print("\nSimulating concurrent transmissions with CSMA/CD...")
    print("This will demonstrate how devices detect collisions and use backoff algorithms")
    print("Watch the logs to see the CSMA/CD protocol in action")
    
    # Define a function to send messages with a delay
    def delayed_send(delay, source, message, target):
        print(f"Scheduling {source} to send message in {delay:.2f} seconds")
        time.sleep(delay)
        print(f"{source} attempting to send: '{message}'")
        network.send_message(source, message, target)
    
    # Start multiple transmissions with overlapping timing to create collision scenarios
    threads = []
    
    # First transmission
    t1 = threading.Thread(target=delayed_send, args=(0.1, "PC1", "Message from PC1", "PC3"))
    threads.append(t1)
    
    # Second transmission (likely to collide with first)
    t2 = threading.Thread(target=delayed_send, args=(0.15, "PC2", "Message from PC2", "PC4"))

    threads.append(t2)
    
    # Third transmission (after a delay, may avoid collision)
    t3 = threading.Thread(target=delayed_send, args=(1.0, "PC4", "Message from PC4", "PC1"))
    threads.append(t3)
    
    # Fourth transmission (even later, should avoid collision)
    t4 = threading.Thread(target=delayed_send, args=(2.0, "PC3", "Message from PC3", "PC2"))
    threads.append(t4)
    
    # Start all threads
    for t in threads:
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    # Wait a bit more to ensure all transmissions complete
    time.sleep(2)
    
    # Display received messages
    print("\nMessages received by devices:")
    for name, device in network.devices.items():
        print(f"{name} received messages:")
        for data, source in device.received_messages:
            print(f"  '{data}' from {source}")
    
    print("\nCSMA/CD Demonstration Complete")
    print("Check the logs for detailed information about carrier sensing, collisions, and backoff")
    
    return network


if __name__ == "__main__":
    interactive_cli()