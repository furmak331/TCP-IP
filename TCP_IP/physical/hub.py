"""
Hub implementation for the TCP/IP Network Simulator.
"""

from TCP_IP.physical.device import Device

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
