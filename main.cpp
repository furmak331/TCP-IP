#include "Network.h"
#include <iostream>
#include <string>

void printHelp() {
    cout << "\nTCP/IP Network Simulator Commands:" << endl;
    cout << "-----------------------------" << endl;
    cout << "1. Run simple test" << endl;
    cout << "2. Create custom network" << endl;  
    cout << "3. Exit" << endl;                 
    cout << "Enter your choice: ";
}

void runCustomNetwork() {
    Network network;
    string input;
    int deviceCount = 0;
    int hubCount = 0;
    
    cout << "\n=== Custom Network Creation ===" << endl;
    
    // First, create devices
    while (true) {
        cout << "\nCreate a new device? (pc/hub/done): ";
        cin >> input;
        
        if (input == "done") {
            break;
        } else if (input == "pc") {
            string name;
            cout << "Enter device name (or leave empty for auto-name): ";
            cin.ignore();
            getline(cin, name);
            
            network.createEndDevice(name);
            deviceCount++;
            cout << "Device created. Total devices: " << deviceCount << endl;
        } else if (input == "hub") {
            string name;
            cout << "Enter hub name (or leave empty for auto-name): ";
            cin.ignore();
            getline(cin, name);
            
            network.createHub(name);
            hubCount++;
            cout << "Hub created. Total hubs: " << hubCount << endl;
        } else {
            cout << "Invalid option. Try again." << endl;
        }
    }
    
    // Get a list of all devices to connect them
    const vector<Device*>& devices = network.getDevices();
    
    // Print all devices
    cout << "\nAvailable Devices:" << endl;
    for (int i = 0; i < devices.size(); i++) {
        cout << i << ". " << devices[i]->getName();
        if (dynamic_cast<Hub*>(devices[i])) {
            cout << " (Hub)";
        }
        cout << endl;
    }
    
    // Now connect devices
    while (true) {
        cout << "\nCreate a connection? (yes/no): ";
        cin >> input;
        
        if (input == "no") {
            break;
        } else if (input == "yes") {
            int device1, device2;
            
            cout << "Select first device (number): ";
            cin >> device1;
            cout << "Select second device (number): ";
            cin >> device2;
            
            if (device1 < 0 || device1 >= devices.size() || device2 < 0 || device2 >= devices.size()) {
                cout << "Invalid device numbers." << endl;
                continue;
            }
            
            // Check device types
            Hub* hub = dynamic_cast<Hub*>(devices[device1]);
            EndDevice* endDevice = dynamic_cast<EndDevice*>(devices[device2]);
            
            if (hub && endDevice) {
                network.connectToHub(hub, endDevice);
                cout << "Connected " << endDevice->getName() << " to " << hub->getName() << endl;
            } else {
                hub = dynamic_cast<Hub*>(devices[device2]);
                endDevice = dynamic_cast<EndDevice*>(devices[device1]);
                
                if (hub && endDevice) {
                    network.connectToHub(hub, endDevice);
                    cout << "Connected " << endDevice->getName() << " to " << hub->getName() << endl;
                } else {
                    // Try to connect two end devices
                    EndDevice* end1 = dynamic_cast<EndDevice*>(devices[device1]);
                    EndDevice* end2 = dynamic_cast<EndDevice*>(devices[device2]);
                    
                    if (end1 && end2) {
                        network.connectDevices(end1, end2);
                        cout << "Connected " << end1->getName() << " to " << end2->getName() << endl;
                    } else {
                        cout << "Cannot connect these devices (unsupported connection type)." << endl;
                    }
                }
            }
        } else {
            cout << "Invalid option. Try again." << endl;
        }
    }
    
    // Now send messages
    while (true) {
        cout << "\nSend a message? (yes/no): ";
        cin >> input;
        
        if (input == "no") {
            break;
        } else if (input == "yes") {
            int deviceIndex;
            string message;
            
            cout << "Select sending device (number): ";
            cin >> deviceIndex;
            
            if (deviceIndex < 0 || deviceIndex >= devices.size()) {
                cout << "Invalid device number." << endl;
                continue;
            }
            
            // Check if it's an end device
            EndDevice* sender = dynamic_cast<EndDevice*>(devices[deviceIndex]);
            if (!sender) {
                cout << "Selected device cannot send messages (not an end device)." << endl;
                continue;
            }
            
            cout << "Enter message: ";
            cin.ignore();
            getline(cin, message);
            
            sender->sendData(message);
            cout << "Message sent from " << sender->getName() << endl;
        } else {
            cout << "Invalid option. Try again." << endl;
        }
    }
    
    // Save network topology
    network.saveTopologyToFile("custom_network.txt");
    cout << "\nCustom network simulation complete. Check the log files in the 'logs' directory." << endl;
}

int main() {
    cout << "Welcome to TCP/IP Network Simulator" << endl;
    
    while (true) {
        printHelp();
        
        int choice;
        cin >> choice;
        
        switch (choice) {
            case 1: {
                Network network;
                network.runSimpleTest();
                break;
            }
            case 2:
                runCustomNetwork();
                break;
            case 3:
                cout << "Exiting simulator. Goodbye!" << endl;
                return 0;
            default:
                cout << "Invalid option. Please try again." << endl;
        }
    }
    
    return 0;
}