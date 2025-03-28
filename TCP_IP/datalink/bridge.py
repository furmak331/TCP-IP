"""
Bridge implementation for the TCP/IP Network Simulator.
"""

from TCP_IP.physical.device import Device

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
