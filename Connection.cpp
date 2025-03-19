#include "Connection.h"
#include "Device.h"
#include "EndDevice.h"

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
        // Check if deviceB is an EndDevice and sender is an EndDevice
        EndDevice* senderEnd = dynamic_cast<EndDevice*>(sender);
        EndDevice* receiverEnd = dynamic_cast<EndDevice*>(deviceB);
        
        if (senderEnd && receiverEnd) {
            // Both are EndDevices - include sender name
            receiverEnd->receiveData(data, portB, senderEnd->getName());
        } else {
            // Standard transmission
            deviceB->receiveData(data, portB);
        }
    } 
    else if (sender == deviceB) {
        // Device B is sending to Device A
        // Check if deviceA is an EndDevice and sender is an EndDevice
        EndDevice* senderEnd = dynamic_cast<EndDevice*>(sender);
        EndDevice* receiverEnd = dynamic_cast<EndDevice*>(deviceA);
        
        if (senderEnd && receiverEnd) {
            // Both are EndDevices - include sender name
            receiverEnd->receiveData(data, portA, senderEnd->getName());
        } else {
            // Standard transmission
            deviceA->receiveData(data, portA);
        }
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