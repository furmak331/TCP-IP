#include "EndDevice.h"
#include "Connection.h"

// Constructor
EndDevice::EndDevice(const string& name) : Device(name) {
}

// Handle incoming data
void EndDevice::receiveData(const string& data, int incomingPort) {
    // Print to console
    cout << name << " received: " << data << " on port " << incomingPort << endl;
    
    // Save message to history
    messageHistory.push_back(data);
}

// Send data through all connections
void EndDevice::sendData(const string& data) {
    // Check if we have any connections
    if (connections.empty()) {
        cout << "No connections available to send data!" << endl;
        return;
    }
    
    // Notify that we're sending
    cout << name << " sending: " << data << endl;
    
    // Send to all connections
    for (Connection* connection : connections) {
        connection->transmitData(data, this);
    }
}

// Show all received messages
void EndDevice::showMessageHistory() {
    cout << "\nMessage history for " << name << ":" << endl;
    
    if (messageHistory.empty()) {
        cout << "  No messages received yet." << endl;
        return;
    }
    
    for (int i = 0; i < messageHistory.size(); i++) {
        cout << "  " << (i+1) << ". " << messageHistory[i] << endl;
    }
}