"""
Command-line interface for the TCP/IP Network Simulator.
"""

import time
import threading
from TCP_IP.network import Network
from TCP_IP.config import ERROR_INJECTION_RATE, CSMA_CD_SLOT_TIME, CSMA_CD_MAX_ATTEMPTS, BUSY_TIME_RANGE

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
            print("  add link <name> [dev1] [dev2] - Add a new link between devices")
            print("  remove device <name>        - Remove a device")
            print("  remove hub <name>           - Remove a hub")
            print("  remove bridge <name>        - Remove a bridge")
            print("  remove switch <name>        - Remove a switch")
            print("  remove link <name>          - Remove a link")
            print("  connect <link> <endpoint>   - Connect an endpoint to a link")
            print("  disconnect <link> <endpoint> - Disconnect an endpoint from a link")
            print("  send <source> <message> [target] - Send a message")
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
            
            if link_name not in network.links:
                print(f"Error: Link '{link_name}' not found")
                continue
            
            endpoint = (network.devices.get(endpoint_name) or 
                        network.hubs.get(endpoint_name) or 
                        network.bridges.get(endpoint_name) or 
                        network.switches.get(endpoint_name))
            
            if not endpoint:
                print(f"Error: Endpoint '{endpoint_name}' not found")
                continue
            
            link = network.links[link_name]
            try:
                link.connect_endpoint(endpoint)
                print(f"Connected {endpoint_name} to {link_name}")
            except ValueError as e:
                print(f"Error: {e}")
        
        elif parts[0] == "disconnect":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            link_name = parts[1]
            endpoint_name = parts[2]
            
            if link_name not in network.links:
                print(f"Error: Link '{link_name}' not found")
                continue
            
            endpoint = (network.devices.get(endpoint_name) or 
                        network.hubs.get(endpoint_name) or 
                        network.bridges.get(endpoint_name) or 
                        network.switches.get(endpoint_name))
            
            if not endpoint:
                print(f"Error: Endpoint '{endpoint_name}' not found")
                continue
            
            link = network.links[link_name]
            link.disconnect_endpoint(endpoint)
            print(f"Disconnected {endpoint_name} from {link_name}")
        
        elif parts[0] == "send":
            if len(parts) < 3:
                print("Error: Insufficient arguments")
                continue
            
            source_name = parts[1]
            message = parts[2]
            target_name = parts[3] if len(parts) > 3 else None
            
            network.send_message(source_name, message, target_name)
        
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
        
        elif parts[0] == "demo" and len(parts) > 1:
            if parts[1] == "error":
                demonstrate_error_control(network)
            elif parts[1] == "csmacd":
                demonstrate_csma_cd(network)
            else:
                print(f"Error: Unknown demo type '{parts[1]}'")
        
        else:
            print(f"Error: Unknown command '{parts[0]}'")


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
