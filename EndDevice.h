#pragma once

#include "Device.h"
#include <vector>
#include <fstream>
#include <string>

using namespace std;

// Represents end devices like computers
class EndDevice : public Device {
private:
    string logFilePath;           // Path to the log file
    
    // Helper method to log messages to file
    void logMessage(const string& message);

public:
    // Constructor
    EndDevice(const string& name);
    
    // Receive data from a connection
    void receiveData(const string& data, int incomingPort, const string& senderName = "") override;
    
    // Send data through all connections
    void sendData(const string& data) override;
    
    // Get log file path
    string getLogFilePath() const;
};