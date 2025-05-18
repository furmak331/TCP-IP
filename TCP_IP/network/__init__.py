# Import the Network class from the network.py file within this package
from .network import Network

# You might also want to import other key classes from this package here
# from .router import Router
# from .ip_address import IPAddress
# from .packet import Packet

# This makes 'Network' available when someone does 'from TCP_IP.network import Network'
__all__ = ['Network'] # Add other classes here if you import them above
