#pragma once

#include "Device.h"
#include <map>
#include <string>
#include <fstream>

using namespace std;

// Represents a network hub that broadcasts data
class Hub : public Device {
private:
    int nextPort;          // Next available port number
    string logFilePath;    // Path to the log file
    
    // Helper method to log messages to file
    void logMessage(const string& message);

public:
    // Constructor
    Hub(const string& name);
    
    // Connect a device to this hub
    int connectDevice(Device* device);
    
    // Handle incoming data
    void receiveData(const string& data, int incomingPort, const string& senderName = "") override;
    
    // Hubs don't send data, only forward it
    void sendData(const string& data) override;
    
    // Get log file path
    string getLogFilePath() const;
};
