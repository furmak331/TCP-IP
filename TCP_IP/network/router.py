class Router(Device):
    """Implements a router that forwards packets between networks."""
    
    def __init__(self, name):
        super().__init__(name)
        self.routing_table = {}  # Maps network prefixes to interfaces
        self.interfaces = []     # Network interfaces with IP addresses