#pragma once

#include <string>

using namespace std;

// Forward declaration
class Device;

// Represents a physical connection between two devices
class Connection {
private:
    Device* deviceA;       // First device
    Device* deviceB;       // Second device
    int portA;             // Port number on device A
    int portB;             // Port number on device B

public:
    // Constructor - creates a connection between two devices
    Connection(Device* devA, Device* devB, int portA, int portB);
    
    // Send data from one device to the other
    void transmitData(const string& data, Device* sender);
    
    // Get the device on the other end of the connection
    Device* getOtherDevice(Device* device);
    
    // Get the port number for a given device
    int getPortNumber(Device* device);
};