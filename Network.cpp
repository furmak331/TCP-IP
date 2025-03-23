#include "Network.h"
#include "Connection.h"
#include <iostream>
#include <fstream>
#include <random>
#include <chrono>

// Constructor
Network::Network() {
    nextId = 1;  // Start IDs at 1
}

// Destructor - free allocated memory
Network::~Network() {
    // Delete all devices
    for (Device* device : devices) {
        delete device;
    }
    
    // Delete all connections
    for (Connection* connection : connections) {
        delete connection;
    }
}

// Create a new end device
EndDevice* Network::createEndDevice(const string& name) {
    // Generate a name if none provided
    string deviceName;
    if (name.empty()) {
        deviceName = "PC" + to_string(nextId++);
    } else {
        deviceName = name;
    }
    
    // Create the device
    EndDevice* device = new EndDevice(deviceName);
    
    // Add to the network
    devices.push_back(device);
    
    return device;
}

// Create a new hub
Hub* Network::createHub(const string& name) {
    // Generate a name if none provided
    string hubName;
    if (name.empty()) {
        hubName = "Hub" + to_string(nextId++);
    } else {
        hubName = name;
    }
    
    // Create the hub
    Hub* hub = new Hub(hubName);
    
    // Add to the network
    devices.push_back(hub);
    
    return hub;
}

// Connect two end devices directly
void Network::connectDevices(EndDevice* dev1, EndDevice* dev2) {
    // Create a new connection
    Connection* connection = new Connection(dev1, dev2, 0, 0);
    
    // Add to the devices
    dev1->addConnection(connection);
    dev2->addConnection(connection);
    
    // Add to the network
    connections.push_back(connection);
}

// Connect an end device to a hub
void Network::connectToHub(Hub* hub, EndDevice* device) {
    // Let the hub create the connection
    hub->connectDevice(device);
}

// Save network topology to a file
void Network::saveTopologyToFile(const string& filename) {
    ofstream file(filename);
    if (!file.is_open()) {
        cout << "Failed to open file: " << filename << endl;
        return;
    }
    
    file << "NETWORK TOPOLOGY" << endl;
    file << "================" << endl << endl;
    
    // List all devices
    file << "Devices (" << devices.size() << "):" << endl;
    for (Device* device : devices) {
        file << "  - " << device->getName() << endl;
        
        // If it's an EndDevice, list its log file
        EndDevice* endDevice = dynamic_cast<EndDevice*>(device);
        if (endDevice) {
            file << "    Log file: " << endDevice->getLogFilePath() << endl;
        }
        
        // If it's a Hub, list its log file
        Hub* hub = dynamic_cast<Hub*>(device);
        if (hub) {
            file << "    Log file: " << hub->getLogFilePath() << endl;
        }
    }
    
    file << endl << "Total connections: " << connections.size() << endl;
    file.close();
    
    cout << "Network topology saved to " << filename << endl;
}

// Run a simple test with a few devices and messages
void Network::runSimpleTest() {
    cout << "Running simple network test..." << endl;
    
    // Create devices
    EndDevice* pc1 = createEndDevice("PC1");
    EndDevice* pc2 = createEndDevice("PC2");
    Hub* hub = createHub("MainHub");
    EndDevice* pc3 = createEndDevice("PC3");
    
    // Connect devices
    connectToHub(hub, pc1);
    connectToHub(hub, pc2);
    connectToHub(hub, pc3);
    
    // Send some test messages
    pc1->sendData("Hello from PC1 to everyone!");
    pc2->sendData("PC2 responding to the network.");
    pc3->sendData("This is PC3, checking in.");
    
    // Save network info
    saveTopologyToFile();
    
    cout << "Test complete. Check the log files in the 'logs' directory." << endl;
}


// Get all devices
const vector<Device*>& Network::getDevices() const {
    return devices;
}