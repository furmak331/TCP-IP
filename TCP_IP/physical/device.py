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

class Device:
    """Base class for all network devices."""
    
    def __init__(self, name):
        self.name = name
        self.mac_address = MACAddress()
        self.connections = []  # List of links connected to this device
        self.received_messages = []  # Messages received by this device
        self.logger = setup_logger(f"{self.name}", f"{self.name}")
        self.logger.info(f"Device {self.name} created with MAC {self.mac_address}")
        
        # Data Link Layer properties
        self.next_sequence_number = 0
        self.expected_sequence_number = 0
        self.window_size = 4  # Window size for sliding window protocol
        self.timeout = 1.0  # Timeout in seconds for retransmission
        self.unacknowledged_frames = {}  # sequence_number -> (frame, timestamp)
        self.buffer = []  # Buffer for received out-of-order frames
        self.use_go_back_n = False  # Default to Stop-and-Wait
    
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
    
    def __str__(self):
        return f"Device({self.name}, MAC={self.mac_address})"
