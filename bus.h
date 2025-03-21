#pragma once

#include "Device.h"
#include <vector>
#include <string>

using namespace std;

// Bus class - implements a bus network topology
// In a bus topology, all devices connect to a single communication line
class Bus : public Device {
private:
    vector<Device*> connectedDevices;  // Devices connected to this bus
    string logFilePath;                // Path to log file
    
    // Helper to log messages to file
    void logMessage(const string& message);

public:
    // Constructor
    Bus(const string& name = "Bus");
    
    // Connect a device to the bus
    void connectDevice(Device* device);
    

    // Handle incoming data - broadcasts to all other devices
    void receiveData(const string& data, int incomingPort, const string& senderName = "");
    
    // Buses don't initiate sending data
    void sendData(const string& data) override;
    
    // Get log file path
    string getLogFilePath() const;
};