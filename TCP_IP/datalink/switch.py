"""
Switch implementation for the TCP/IP Network Simulator.
"""

from TCP_IP.datalink.bridge import Bridge

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
