#pragma once

#include <iostream>
#include <vector>
#include <string>

using namespace std;

// Forward declarations
class Connection;

// Base Device class - represents any network device
class Device {
protected:
    string name;                           // Device name
    vector<Connection*> connections;       // Connections to other devices

public:
    // Constructor
    Device(const string& deviceName);
    
    // Get the name of this device
    string getName();
    
    // Add a connection to this device
    void addConnection(Connection* connection);
    
    // Methods that must be implemented by derived classes
    virtual void receiveData(const string& data, int incomingPort) = 0;
    virtual void sendData(const string& data) = 0;
};