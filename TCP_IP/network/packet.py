class Packet:
    """Represents a network layer packet with IP addressing."""
    
    def __init__(self, source_ip, destination_ip, data, ttl=64, protocol=0):
        self.source_ip = source_ip
        self.destination_ip = destination_ip
        self.data = data
        self.ttl = ttl
        self.protocol = protocol
        self.checksum = self._calculate_checksum()
        self.timestamp = time.time()  # For timeout calculations
    
    def _calculate_checksum(self):
        """Calculate a simple checksum for error detection"""
        # Use a simple sum of bytes as checksum for demonstration
        checksum = 0
        # Include header fields in checksum
        for c in str(self.source_ip) + str(self.destination_ip) + str(self.ttl) + str(self.protocol):
            checksum = (checksum + ord(c)) % 256
        # Include data in checksum
        for c in self.data:
            checksum = (checksum + ord(c)) % 256
        return checksum
    
    def is_valid(self):
        """Check if the packet has a valid checksum"""
        return self._calculate_checksum() == self.checksum
