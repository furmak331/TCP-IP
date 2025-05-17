"""
Frame implementation for the TCP/IP Network Simulator.
"""

import time
import random
from enum import Enum

class FrameType(Enum):
    """Enum for different frame types"""
    DATA = 1
    ACK = 2
    NAK = 3
    ARP_REQUEST = 3
    ARP_REPLY = 4


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
