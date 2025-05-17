"""
Network implementation for the TCP/IP Network Simulator.
"""

from TCP_IP.utils.logging_config import setup_logger
from TCP_IP.physical.device import Device
from TCP_IP.physical.hub import Hub
from TCP_IP.physical.link import Link
from TCP_IP.datalink.bridge import Bridge
from TCP_IP.datalink.switch import Switch
from TCP_IP.network.router import Router

class Network:
    """Manages the network topology and message flow."""
    
    def __init__(self, name):
        self.name = name
        self.devices = {}  # name -> Device
        self.hubs = {}     # name -> Hub
        self.bridges = {}  # name -> Bridge
        self.switches = {} # name -> Switch
        self.routers = {}  # Add routers dictionary
        self.links = {}    # name -> Link
        self.logger = setup_logger(f"Network_{name}", f"network_{name}")
    
    def add_device(self, name):
        """Add a new device to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        device = Device(name)
        self.devices[name] = device
        self.logger.info(f"Added device: {name}")
        return device
    
    def add_hub(self, name):
        """Add a new hub to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        hub = Hub(name)
        self.hubs[name] = hub
        self.logger.info(f"Added hub: {name}")
        return hub
    
    def add_bridge(self, name):
        """Add a new bridge to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        bridge = Bridge(name)
        self.bridges[name] = bridge
        self.logger.info(f"Added bridge: {name}")
        return bridge
    
    def add_switch(self, name):
        """Add a new switch to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches:
            self.logger.error(f"A device with name '{name}' already exists")
            return None
        
        switch = Switch(name)
        self.switches[name] = switch
        self.logger.info(f"Added switch: {name}")
        return switch
    
    def add_router(self, name):
        """Add a new router to the network."""
        if name in self.devices or name in self.hubs or name in self.bridges or name in self.switches or name in self.routers:
            self.logger.error(f"A device/router with name '{name}' already exists")
            return None
        
        router = Router(name)
        self.routers[name] = router
        self.logger.info(f"Added router: {name}")
        return router
    
    def add_link(self, name, endpoint1_name=None, endpoint2_name=None):
        """Add a new link between two endpoints (devices or hubs)."""
        if name in self.links:
            self.logger.error(f"A link with name '{name}' already exists")
            return None
        
        endpoint1 = None
        endpoint2 = None
        
        if endpoint1_name:
            endpoint1 = (self.devices.get(endpoint1_name) or 
                         self.hubs.get(endpoint1_name) or 
                         self.bridges.get(endpoint1_name) or 
                         self.switches.get(endpoint1_name))
            if not endpoint1:
                self.logger.error(f"Endpoint '{endpoint1_name}' not found")
                return None
        
        if endpoint2_name:
            endpoint2 = (self.devices.get(endpoint2_name) or 
                         self.hubs.get(endpoint2_name) or 
                         self.bridges.get(endpoint2_name) or 
                         self.switches.get(endpoint2_name))
            if not endpoint2:
                self.logger.error(f"Endpoint '{endpoint2_name}' not found")
                return None
        
        link = Link(name, endpoint1, endpoint2)
        self.links[name] = link
        self.logger.info(f"Added link: {name} connecting {endpoint1_name or 'None'} and {endpoint2_name or 'None'}")
        return link
    
    def remove_device(self, name):
        """Remove a device from the network."""
        device_to_remove = self.get_device(name)

        if not device_to_remove:
            self.logger.error(f"Device/Router '{name}' not found")
            return False

        # Disconnect from all links
        for link in device_to_remove.connections.copy():
            link.disconnect_endpoint(device_to_remove)

        # Remove from the correct dictionary
        if name in self.devices:
            del self.devices[name]
        elif name in self.hubs:
            del self.hubs[name]
        elif name in self.bridges:
            del self.bridges[name]
        elif name in self.switches:
            del self.switches[name]
        elif name in self.routers:
            del self.routers[name]

        self.logger.info(f"Removed device/router: {name}")
        return True
    
    def remove_hub(self, name):
        """Remove a hub from the network."""
        if name not in self.hubs:
            self.logger.error(f"Hub '{name}' not found")
            return False
        
        hub = self.hubs[name]
        
        # Disconnect from all links
        for link in hub.connections.copy():
            link.disconnect_endpoint(hub)
        
        del self.hubs[name]
        self.logger.info(f"Removed hub: {name}")
        return True
    
    def remove_bridge(self, name):
        """Remove a bridge from the network."""
        if name not in self.bridges:
            self.logger.error(f"Bridge '{name}' not found")
            return False
        
        bridge = self.bridges[name]
        
        # Disconnect from all links
        for link in bridge.connections.copy():
            link.disconnect_endpoint(bridge)
        
        del self.bridges[name]
        self.logger.info(f"Removed bridge: {name}")
        return True
    
    def remove_switch(self, name):
        """Remove a switch from the network."""
        if name not in self.switches:
            self.logger.error(f"Switch '{name}' not found")
            return False
        
        switch = self.switches[name]
        
        # Disconnect from all links
        for link in switch.connections.copy():
            link.disconnect_endpoint(switch)
        
        del self.switches[name]
        self.logger.info(f"Removed switch: {name}")
        return True
    
    def remove_link(self, name):
        """Remove a link from the network."""
        if name not in self.links:
            self.logger.error(f"Link '{name}' not found")
            return False
        
        link = self.links[name]
        
        # Disconnect endpoints
        if link.endpoint1:
            link.disconnect_endpoint(link.endpoint1)
        if link.endpoint2:
            link.disconnect_endpoint(link.endpoint2)
        
        del self.links[name]
        self.logger.info(f"Removed link: {name}")
        return True
    
    def send_message(self, source_name, message, target_name=None):
        """Send a message from a source device to a target device."""
        source = (self.devices.get(source_name) or 
                  self.hubs.get(source_name) or 
                  self.bridges.get(source_name) or 
                  self.switches.get(source_name))
        
        if not source:
            self.logger.error(f"Source device '{source_name}' not found")
            return False
        
        target = None
        target_mac = None
        
        if target_name:
            target = (self.devices.get(target_name) or 
                      self.hubs.get(target_name) or 
                      self.bridges.get(target_name) or 
                      self.switches.get(target_name))
            
            if not target:
                self.logger.error(f"Target device '{target_name}' not found")
                return False
            
            target_mac = str(target.mac_address)
        
        return source.send_message(message, target_mac)
    
    def enable_go_back_n(self, device_name, window_size=4):
        """Enable Go-Back-N protocol for a device."""
        device = (self.devices.get(device_name) or 
                  self.hubs.get(device_name) or 
                  self.bridges.get(device_name) or 
                  self.switches.get(device_name))
        
        if not device:
            self.logger.error(f"Device '{device_name}' not found")
            return False
        
        device.use_go_back_n = True
        device.window_size = window_size
        self.logger.info(f"Enabled Go-Back-N protocol for {device_name} with window size {window_size}")
        return True
    
    def display_network(self):
        """Display the current network topology."""
        print(f"\n=== Network: {self.name} ===")
        
        print("\nDevices:")
        for name, device in self.devices.items():
            print(f"  {name} (MAC: {device.mac_address}, IP: {device.ip_address.address if device.ip_address else 'None'})")
            if device.arp_table:
                 print("    ARP Table:")
                 for ip, mac in device.arp_table.items():
                     print(f"      {ip} -> {mac}")
        
        print("\nRouters:")
        for name, router in self.routers.items():
            print(f"  {name} (MAC: {router.mac_address})")
            if router.interfaces:
                 print("    Interfaces:")
                 for interface in router.interfaces:
                     print(f"      {interface.name}: {interface.ip_address}, MAC: {interface.mac_address}")
            if router.routing_table:
                 print("    Routing Table:")
                 # Sort routes for consistent display (optional)
                 sorted_routes = sorted(router.routing_table.items(), key=lambda item: item[0].prefixlen, reverse=True)
                 for dest, (output_int, next_hop) in sorted_routes:
                     print(f"      {dest} -> via {output_int.name}, next hop {next_hop.address if next_hop else 'direct'}")
            if router.arp_table:
                 print("    ARP Table:")
                 for ip, mac in router.arp_table.items():
                     print(f"      {ip} -> {mac}")
        
        print("\nHubs:")
        for name, hub in self.hubs.items():
            print(f"  {name} (MAC: {hub.mac_address})")
        
        print("\nBridges:")
        for name, bridge in self.bridges.items():
            print(f"  {name} (MAC: {bridge.mac_address})")
            if bridge.mac_table:
                print("    MAC Table:")
                for mac, port in bridge.mac_table.items():
                    print(f"      {mac} -> Port {port}")
        
        print("\nSwitches:")
        for name, switch in self.switches.items():
            print(f"  {name} (MAC: {switch.mac_address})")
            if switch.mac_table:
                print("    MAC Table:")
                for mac, port in switch.mac_table.items():
                    print(f"      {mac} -> Port {port}")
            if switch.vlan_table:
                print("    VLANs:")
                for vlan_id, ports in switch.vlan_table.items():
                    print(f"      VLAN {vlan_id}: Ports {sorted(ports)}")
        
        print("\nLinks:")
        for name, link in self.links.items():
            endpoint1_name = link.endpoint1.name if link.endpoint1 else "None"
            endpoint2_name = link.endpoint2.name if link.endpoint2 else "None"
            print(f"  {name}: {endpoint1_name} <-> {endpoint2_name}")
        
        print("\n")
    
    def __str__(self):
        return (f"Network({self.name}, {len(self.devices)} devices, {len(self.hubs)} hubs, "
                f"{len(self.bridges)} bridges, {len(self.switches)} switches, {len(self.links)} links)")

    def get_device(self, name):
        """Get a device (including routers, hubs, etc.) by name."""
        return (self.devices.get(name) or
                self.hubs.get(name) or
                self.bridges.get(name) or
                self.switches.get(name) or
                self.routers.get(name))

    def send_packet(self, source_name, destination_ip_str, data, protocol=0):
        """Send a packet from a source device to a target IP address."""
        source = self.get_device(source_name)

        if not source:
            self.logger.error(f"Source device/router '{source_name}' not found")
            return False

        # Use the device's send_packet method
        return source.send_packet(destination_ip_str, data, protocol) 