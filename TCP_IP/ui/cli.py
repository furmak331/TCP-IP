"""
Command-line interface for the TCP/IP Network Simulator.
"""

import time
import threading
from TCP_IP.network import Network
from TCP_IP.config import ERROR_INJECTION_RATE, CSMA_CD_SLOT_TIME, CSMA_CD_MAX_ATTEMPTS, BUSY_TIME_RANGE
from TCP_IP.network.router import Router
from TCP_IP.network.ip_address import IPAddress
from TCP_IP.network.packet import Packet

def interactive_cli():
    """Provide an interactive command-line interface for the network simulator."""
    network = Network("TestNetwork")
    
    print("TCP/IP Network Simulator")
    print("Type 'help' for a list of commands")
    
    while True:
        command = input("\nEnter command: ").strip().lower()
        parts = command.split()
        
        if not parts:
            continue
        
        if parts[0] == "exit" or parts[0] == "quit":
            print("Exiting simulator...")
            break
        
        elif parts[0] == "help":
            print("\nAvailable commands:")
            print("  add device <name>           - Add a new device")
            print("  add hub <name>              - Add a new hub")
            print("  add bridge <name>           - Add a new bridge")
            print("  add switch <name>           - Add a new switch")
            print("  add router <name>           - Add a new router")
            print("  add link <name> [dev1] [dev2] - Add a new link between devices")
            print("  remove device <name>        - Remove a device")
            print("  remove hub <name>           - Remove a hub")
            print("  remove bridge <name>        - Remove a bridge")
            print("  remove switch <name>        - Remove a switch")
            print("  remove router <name>        - Remove a router")
            print("  remove link <name>          - Remove a link")
            print("  connect <link> <endpoint>   - Connect an endpoint to a link")
            print("  disconnect <link> <endpoint> - Disconnect an endpoint from a link")
            print("  assign ip <device> <ip_address> [subnet_mask] - Assign IP to a device")
            print("  set gateway <device> <gateway_ip> - Set default gateway for a device")
            print("  add route <router> <destination_cidr> <output_interface_ip> [next_hop_ip] - Add static route")
            print("  remove route <router> <destination_cidr> - Remove static route")
            print("  send message <source> <message> [target_mac] - Send a Data Link message")
            print("  send packet <source> <destination_ip> <data> [protocol] - Send a Network Layer packet")
            print("  enable gbn <device> [window_size] - Enable Go-Back-N protocol")
            print("  display                     - Display network topology")
            print("  demo error                  - Demonstrate error control")
            print("  demo csmacd                 - Demonstrate CSMA/CD protocol")
            print("  help                        - Show this help message")
            print("  exit/quit                   - Exit the simulator")
        
        elif parts[0] == "add":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            if parts[1] == "device":
                network.add_device(parts[2])
            
            elif parts[1] == "hub":
                network.add_hub(parts[2])
            
            elif parts[1] == "bridge":
                network.add_bridge(parts[2])
            
            elif parts[1] == "switch":
                network.add_switch(parts[2])
            
            elif parts[1] == "router":
                network.add_router(parts[2])
            
            elif parts[1] == "link":
                if len(parts) == 3:
                    network.add_link(parts[2])
                elif len(parts) == 4:
                    network.add_link(parts[2], parts[3])
                elif len(parts) >= 5:
                    network.add_link(parts[2], parts[3], parts[4])
            
            else:
                print(f"Error: Unknown entity type '{parts[1]}'")
        
        elif parts[0] == "remove":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            if parts[1] == "device":
                network.remove_device(parts[2])
            
            elif parts[1] == "hub":
                network.remove_hub(parts[2])
            
            elif parts[1] == "bridge":
                network.remove_bridge(parts[2])
            
            elif parts[1] == "switch":
                network.remove_switch(parts[2])
            
            elif parts[1] == "router":
                network.remove_device(parts[2])
            
            elif parts[1] == "link":
                network.remove_link(parts[2])
            
            else:
                print(f"Error: Unknown entity type '{parts[1]}'")
        
        elif parts[0] == "connect":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            link_name = parts[1]
            endpoint_name = parts[2]
            
            link = network.links.get(link_name)
            if not link:
                print(f"Error: Link '{link_name}' not found")
                continue
            
            endpoint = network.get_device(endpoint_name)
            if not endpoint:
                print(f"Error: Endpoint '{endpoint_name}' not found")
                continue
            
            if isinstance(endpoint, Router) and len(parts) >= 5 and parts[3] == "interface":
                interface_ip_str = parts[4]
                subnet_mask_str = parts[5] if len(parts) > 5 else "255.255.255.0"
                endpoint.add_interface(interface_ip_str, subnet_mask_str, link)
                print(f"Connected router {endpoint_name} interface {interface_ip_str} to link {link_name}")
            else:
                link.connect_endpoint(endpoint)
                print(f"Connected {endpoint_name} to {link_name}")
        
        elif parts[0] == "disconnect":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            link_name = parts[1]
            endpoint_name = parts[2]
            
            link = network.links.get(link_name)
            if not link:
                print(f"Error: Link '{link_name}' not found")
                continue
            
            endpoint = network.get_device(endpoint_name)
            if not endpoint:
                print(f"Error: Endpoint '{endpoint_name}' not found")
                continue
            
            if isinstance(endpoint, Router) and len(parts) >= 4 and parts[3] == "interface":
                interface_ip_str = parts[4] if len(parts) > 4 else None
                if interface_ip_str:
                    endpoint.remove_interface(interface_ip_str)
                    print(f"Disconnected router {endpoint_name} interface {interface_ip_str} from link {link_name}")
                else:
                    print("Error: Specify the IP address of the interface to disconnect.")
            else:
                link.disconnect_endpoint(endpoint)
                print(f"Disconnected {endpoint_name} from {link_name}")
        
        elif parts[0] == "assign" and parts[1] == "ip":
            if len(parts) < 4:
                print("Error: Insufficient arguments. Usage: assign ip <device> <ip_address> [subnet_mask]")
                continue
            device_name = parts[2]
            ip_address_str = parts[3]
            subnet_mask_str = parts[4] if len(parts) > 4 else "255.255.255.0"
            
            device = network.get_device(device_name)
            if not device:
                print(f"Error: Device '{device_name}' not found")
                continue
            
            if device.assign_ip_address(ip_address_str, subnet_mask_str):
                print(f"Assigned IP {ip_address_str}/{subnet_mask_str} to {device_name}")
            else:
                print(f"Failed to assign IP to {device_name}")
        
        elif parts[0] == "set" and parts[1] == "gateway":
            if len(parts) < 4:
                print("Error: Insufficient arguments. Usage: set gateway <device> <gateway_ip>")
                continue
            device_name = parts[2]
            gateway_ip_str = parts[3]
            
            device = network.get_device(device_name)
            if not device:
                print(f"Error: Device '{device_name}' not found")
                continue
            
            if hasattr(device, 'set_default_gateway'):
                device.set_default_gateway(gateway_ip_str)
                print(f"Set default gateway for {device_name} to {gateway_ip_str}")
            else:
                print(f"Error: Device '{device_name}' does not support setting a default gateway.")
        
        elif parts[0] == "add" and parts[1] == "route":
            if len(parts) < 5:
                print("Error: Insufficient arguments. Usage: add route <router> <destination_cidr> <output_interface_ip> [next_hop_ip]")
                continue
            router_name = parts[2]
            destination_cidr = parts[3]
            output_interface_ip_str = parts[4]
            next_hop_ip_str = parts[5] if len(parts) > 5 else None
            
            router = network.routers.get(router_name)
            if not router:
                print(f"Error: Router '{router_name}' not found")
                continue
            
            router.add_route(destination_cidr, output_interface_ip_str, next_hop_ip_str)
        
        elif parts[0] == "remove" and parts[1] == "route":
            if len(parts) < 4:
                print("Error: Insufficient arguments. Usage: remove route <router> <destination_cidr>")
                continue
            router_name = parts[2]
            destination_cidr = parts[3]
            
            router = network.routers.get(router_name)
            if not router:
                print(f"Error: Router '{router_name}' not found")
                continue
            
            router.remove_route(destination_cidr)
        
        elif parts[0] == "send":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            if parts[1] == "message":
                source_name = parts[2]
                message = parts[3]
                target_name = parts[4] if len(parts) > 4 else None
                target_mac = None
                if target_name:
                    target_device = network.get_device(target_name)
                    if target_device:
                        target_mac = str(target_device.mac_address)
                    else:
                        print(f"Error: Target device '{target_name}' not found for message send.")
                        continue
                network.send_message(source_name, message, target_mac)
            
            elif parts[1] == "packet":
                if len(parts) < 4:
                    print("Error: Insufficient arguments. Usage: send packet <source> <destination_ip> <data> [protocol]")
                    continue
                source_name = parts[2]
                destination_ip_str = parts[3]
                data = parts[4]
                protocol = int(parts[5]) if len(parts) > 5 else 0
                
                network.send_packet(source_name, destination_ip_str, data, protocol)
            
            else:
                print(f"Error: Unknown send type '{parts[1]}'")
        
        elif parts[0] == "enable" and parts[1] == "gbn":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            device_name = parts[2]
            window_size = int(parts[3]) if len(parts) > 3 else 4
            
            if network.enable_go_back_n(device_name, window_size):
                print(f"Enabled Go-Back-N protocol for {device_name} with window size {window_size}")
            else:
                print(f"Failed to enable Go-Back-N for {device_name}")
        
        elif parts[0] == "display":
            network.display_network()
        
        elif parts[0] == "demo" and parts[1] == "error":
            demonstrate_error_control()
        
        elif parts[0] == "demo" and parts[1] == "csmacd":
            demonstrate_csma_cd()
        
        else:
            print(f"Error: Unknown command '{command}'")


def demonstrate_error_control(network=None):
    """Demonstrate error control in the network simulator"""
    print("\n=== Error Control Demonstration ===")
    
    # Create a network if none provided
    if network is None:
        network = Network("ErrorControlDemo")
    
    # Create devices
    pc1 = network.add_device("PC1")
    pc2 = network.add_device("PC2")
    
    # Create a link between devices
    link = network.add_link("Link1", "PC1", "PC2")
    
    # Enable Go-Back-N for PC1
    network.enable_go_back_n("PC1", window_size=4)
    
    # Display the network
    network.display_network()
    
    # Send a message from PC1 to PC2
    print("\nSending message from PC1 to PC2 with error control...")
    print(f"Error injection rate: {ERROR_INJECTION_RATE*100}%")
    network.send_message("PC1", "This is a test message with error control!", "PC2")
    
    # Wait a bit for message processing to complete
    time.sleep(2)
    
    # Display received messages
    print("\nMessages received by PC2:")
    for data, source in network.devices["PC2"].received_messages:
        print(f"  '{data}' from {source}")
    
    return network


def demonstrate_csma_cd(network=None):
    """Demonstrate CSMA/CD protocol in the network simulator"""
    print("\n=== CSMA/CD Protocol Demonstration ===")
    print(f"Medium busy time range: {BUSY_TIME_RANGE[0]:.2f} to {BUSY_TIME_RANGE[1]:.2f} seconds")
    print(f"Backoff slot time: {CSMA_CD_SLOT_TIME:.3f} seconds")
    print(f"Maximum transmission attempts: {CSMA_CD_MAX_ATTEMPTS}")
    
    # Create a network if none provided
    if network is None:
        network = Network("CSMA_CD_Demo")
    
    # Create devices
    pc1 = network.add_device("PC1")
    pc2 = network.add_device("PC2")
    pc3 = network.add_device("PC3")
    pc4 = network.add_device("PC4")
    
    # Create a hub to simulate a shared medium
    hub = network.add_hub("Hub1")
    
    # Connect all devices to the hub
    link1 = network.add_link("Link1", "PC1", "Hub1")
    link2 = network.add_link("Link2", "PC2", "Hub1")
    link3 = network.add_link("Link3", "PC3", "Hub1")
    link4 = network.add_link("Link4", "PC4", "Hub1")
    
    # Display the network
    network.display_network()
    
    # Simulate concurrent transmissions to demonstrate collision detection
    print("\nSimulating concurrent transmissions with CSMA/CD...")
    print("This will demonstrate how devices detect collisions and use backoff algorithms")
    print("Watch the logs to see the CSMA/CD protocol in action")
    
    # Define a function to send messages with a delay
    def delayed_send(delay, source, message, target):
        print(f"Scheduling {source} to send message in {delay:.2f} seconds")
        time.sleep(delay)
        print(f"{source} attempting to send: '{message}'")
        network.send_message(source, message, target)
    
    # Start multiple transmissions with overlapping timing to create collision scenarios
    threads = []
    
    # First transmission
    t1 = threading.Thread(target=delayed_send, args=(0.1, "PC1", "Message from PC1", "PC3"))
    threads.append(t1)
    
    # Second transmission (likely to collide with first)
    t2 = threading.Thread(target=delayed_send, args=(0.15, "PC2", "Message from PC2", "PC4"))
    threads.append(t2)
    
    # Third transmission (after a delay, may avoid collision)
    t3 = threading.Thread(target=delayed_send, args=(1.0, "PC4", "Message from PC4", "PC1"))
    threads.append(t3)
    
    # Fourth transmission (even later, should avoid collision)
    t4 = threading.Thread(target=delayed_send, args=(2.0, "PC3", "Message from PC3", "PC2"))
    threads.append(t4)
    
    # Start all threads
    for t in threads:
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    # Wait a bit more to ensure all transmissions complete
    time.sleep(2)
    
    # Display received messages
    print("\nMessages received by devices:")
    for name, device in network.devices.items():
        print(f"{name} received messages:")
        for data, source in device.received_messages:
            print(f"  '{data}' from {source}")
    
    print("\nCSMA/CD Demonstration Complete")
    print("Check the logs for detailed information about carrier sensing, collisions, and backoff")
    
    return network
