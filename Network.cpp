#include "Network.h"
#include "Connection.h" // Include the header for the Connection class

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
    
    // Print confirmation
    cout << "Connected " << dev1->getName() << " to " << dev2->getName() << endl;
}

// Connect an end device to a hub
void Network::connectToHub(Hub* hub, EndDevice* device) {
    // Let the hub create the connection
    int portNumber = hub->connectDevice(device);
    
    // Print confirmation
    cout << "Connected " << device->getName() << " to " << hub->getName() 
         << " on port " << portNumber << endl;
}

// Display the network topology
void Network::displayTopology() {
    cout << "\n----- NETWORK TOPOLOGY -----" << endl;
    
    // List all devices
    cout << "Devices (" << devices.size() << "):" << endl;
    for (Device* device : devices) {
        cout << "  - " << device->getName() << endl;
    }
    
    // List all connections
    cout << "Connections (" << connections.size() << ")" << endl;
    
    cout << "---------------------------" << endl;
}