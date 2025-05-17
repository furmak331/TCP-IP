import ipaddress

class IPAddress:
    """Represents an IPv4 address for network layer routing."""
    
    def __init__(self, address=None, subnet_mask="255.255.255.0"):
        self.address = address
        self.subnet_mask = subnet_mask
        self.network_address = self._calculate_network_address(address, subnet_mask)
        self.broadcast_address = self._calculate_broadcast_address(address, subnet_mask)
        self.ip_network = self._get_ip_network(address, subnet_mask) # Store ipaddress.IPv4Network object

    def _calculate_network_address(self, address, subnet_mask):
        """Calculate the network address from the IP address and subnet mask."""
        if not address or not subnet_mask:
            return None
        try:
            # Use the ipaddress module for robust calculation
            network = ipaddress.IPv4Network(f"{address}/{subnet_mask}", strict=False)
            return str(network.network_address)
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
            return None

    def _calculate_broadcast_address(self, address, subnet_mask):
        """Calculate the broadcast address from the IP address and subnet mask."""
        if not address or not subnet_mask:
            return None
        try:
            network = ipaddress.IPv4Network(f"{address}/{subnet_mask}", strict=False)
            return str(network.broadcast_address)
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
            return None

    def _get_ip_network(self, address, subnet_mask):
        """Get the ipaddress.IPv4Network object."""
        if not address or not subnet_mask:
            return None
        try:
            return ipaddress.IPv4Network(f"{address}/{subnet_mask}", strict=False)
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
            return None

    def is_in_network(self, other_ip_address):
        """Check if another IP address is in the same network."""
        if not self.ip_network or not other_ip_address or not other_ip_address.ip_network:
             return False
        try:
            # Check if the other IP address is within this network's range
            return ipaddress.IPv4Address(other_ip_address.address) in self.ip_network
        except ipaddress.AddressValueError:
            return False

    def __str__(self):
        return f"{self.address}/{self.subnet_mask}"

    def __eq__(self, other):
        if isinstance(other, IPAddress):
            return self.address == other.address and self.subnet_mask == other.subnet_mask
        elif isinstance(other, str):
             # Allow comparison with string representation (e.g., "192.168.1.1/24")
             try:
                 other_ip = IPAddress(other.split('/')[0], other.split('/')[1] if '/' in other else "255.255.255.0")
                 return self == other_ip
             except:
                 return False
        return False

    def __hash__(self):
        return hash((self.address, self.subnet_mask))

    def get_network_prefix(self):
        """Return the network address in CIDR notation."""
        if self.ip_network:
            return str(self.ip_network)
        return None
