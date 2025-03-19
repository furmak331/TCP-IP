#include "Device.h"

// Constructor - just sets the name
Device::Device(const string& deviceName) {
    name = deviceName;
}

// Returns the device's name
string Device::getName() const {
    return name;
}

// Adds a connection to this device's list of connections
void Device::addConnection(Connection* connection) {
    connections.push_back(connection);
}