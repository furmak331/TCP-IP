class Packet:
    """Represents a network layer packet with IP addressing."""
    
    def __init__(self, source_ip, destination_ip, data, ttl=64, protocol=0):
        