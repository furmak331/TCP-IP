import time # Assuming time is needed for timestamp

class Packet:
    """Represents a network layer packet with IP addressing."""
    
    def __init__(self, source_ip, destination_ip, data, ttl=64, protocol=0):
        self.source_ip = source_ip # String format "X.X.X.X"
        self.destination_ip = destination_ip # String format "X.X.X.X"
        self.data = data # Payload (can be Transport Layer segment or other data)
        self.ttl = ttl # Time To Live
        self.protocol = protocol # e.g., 6 for TCP, 17 for UDP, 1 for ICMP
        self.checksum = self._calculate_checksum()
        self.timestamp = time.time()  # For potential timeout calculations (less common at Network layer)
    
    def _calculate_checksum(self):
        """Calculate a simple checksum for error detection"""
        # Use a simple sum of bytes as checksum for demonstration
        checksum = 0
        # Include header fields in checksum
        for c in str(self.source_ip) + str(self.destination_ip) + str(self.ttl) + str(self.protocol):
            checksum = (checksum + ord(c)) % 256
        # Include data in checksum (assuming data is string or can be converted)
        try:
            data_str = str(self.data)
            for c in data_str:
                checksum = (checksum + ord(c)) % 256
        except TypeError:
             # Handle cases where data is not easily convertible to string
             pass # Or implement a more robust checksum for arbitrary data

        return checksum
    
    def is_valid(self):
        """Check if the packet has a valid checksum"""
        # Recalculate checksum and compare with stored checksum
        return self._calculate_checksum() == self.checksum
    
    def __str__(self):
        return f"Packet(src={self.source_ip}, dest={self.destination_ip}, ttl={self.ttl}, proto={self.protocol}, data='{self.data}')"
    
    
