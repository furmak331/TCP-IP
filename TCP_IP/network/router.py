class Router(Device):
    """Implements a router that forwards packets between networks."""
    
    def __init__(self, name):
        super().__init__(name)
        self.routing_table = {}  # Maps network prefixes to interfaces
        self.interfaces = []     # Network interfaces with IP addresses
        self.logger = setup_logger(f"Router_{name}", f"router_{name}")
    
    def add_interface(self, ip_address):
        """Add a network interface with the given IP address."""
        self.interfaces.append(ip_address)
        self.logger.info(f"Added interface with IP address {ip_address}")
    
    def remove_interface(self, ip_address):
        """Remove a network interface with the given IP address."""
        if ip_address in self.interfaces:
            self.interfaces.remove(ip_address)
            self.logger.info(f"Removed interface with IP address {ip_address}")
        else:
            self.logger.warning(f"Interface with IP address {ip_address} not found")
    
    def add_route(self, network_prefix, interface):
        """Add a route to the routing table."""
        self.routing_table[network_prefix] = interface
        self.logger.info(f"Added route to network {network_prefix} via interface {interface}")
    
    def remove_route(self, network_prefix):
        """Remove a route from the routing table."""
        if network_prefix in self.routing_table:
            del self.routing_table[network_prefix]
            self.logger.info(f"Removed route to network {network_prefix}")
        else:
            self.logger.warning(f"Route to network {network_prefix} not found")
    
    def forward_packet(self, packet, source_interface):
        """Forward a packet to the appropriate next hop."""
        # Check if the packet is for this router


