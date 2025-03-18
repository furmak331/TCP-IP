#include "Connection.h"
#include "Device.h"

// Constructor
Connection::Connection(Device* devA, Device* devB, int pA, int pB) {
    deviceA = devA;
    deviceB = devB;
    portA = pA;
    portB = pB;
}

// Transmit data from the sender to the other device
void Connection::transmitData(const string& data, Device* sender) {
    // Find out which device is sending and which is receiving
    if (sender == deviceA) {
        // Device A is sending to Device B
        deviceB->receiveData(data, portB);
    } 
    else if (sender == deviceB) {
        // Device B is sending to Device A
        deviceA->receiveData(data, portA);
    }
}

// Get the device on the other end
Device* Connection::getOtherDevice(Device* device) {
    if (device == deviceA) return deviceB;
    if (device == deviceB) return deviceA;
    return nullptr;  // Not connected to this device
}

// Get the port number for a device
int Connection::getPortNumber(Device* device) {
    if (device == deviceA) return portA;
    if (device == deviceB) return portB;
    return -1;  // Invalid port
}