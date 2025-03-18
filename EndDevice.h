#pragma once

#include "Device.h"
#include <vector>

using namespace std;

// Represents end devices like computers
class EndDevice : public Device {
private:
    vector<string> messageHistory;  // Record of received messages

public:
    // Constructor
    EndDevice(const string& name);
    
    // Receive data from a connection
    void receiveData(const string& data, int incomingPort) override;
    
    // Send data through all connections
    void sendData(const string& data) override;
    
    // Show message history (for testing)
    void showMessageHistory();
};