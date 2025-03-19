#pragma once

#include "Device.h"
#include <map>

using namespace std;

// Represents a network hub that broadcasts data
class Hub : public Device {
private:
    int nextPort;  // Next available port number

public:
    // Constructor
    Hub(const string& name);
    
    // Connect a device to this hub
    int connectDevice(Device* device);
    
    // Handle incoming data
    void receiveData(const string& data, int incomingPort) override;
    
    // Hubs don't send data, only forward it
    void sendData(const string& data) override;
};