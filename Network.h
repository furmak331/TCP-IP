#pragma once

#include "EndDevice.h"
#include "Hub.h"
#include <vector>

using namespace std;

// Manages the network topology
class Network {
private:
    vector<Device*> devices;           // All devices in the network
    vector<Connection*> connections;   // All connections in the network
    int nextId;                        // Used for auto-naming devices

public:
    // Constructor
    Network();
    
    // Destructor - cleans up memory
    ~Network();
    
    // Create a new end device
    EndDevice* createEndDevice(const string& name = "");
    
    // Create a new hub
    Hub* createHub(const string& name = "");
    
    // Create a direct connection between two end devices
    void connectDevices(EndDevice* dev1, EndDevice* dev2);
    
    // Connect an end device to a hub
    void connectToHub(Hub* hub, EndDevice* device);
    
    // Display the network topology
    void displayTopology();
};