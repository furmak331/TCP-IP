"""
MAC Address implementation for the TCP/IP Network Simulator.
"""

import random

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