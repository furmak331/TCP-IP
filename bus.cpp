#include "Bus.h"
#include "Connection.h"
#include <ctime>
#include <iomanip>
#include <filesystem>
#include <fstream>

// Helper function to get current timestamp as string (if not already defined)
namespace {
    string getCurrentTimestamp() {
        time_t now = time(0);
        tm* localTime = localtime(&now);
        char buffer[80];
        strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", localTime);
        return string(buffer);
    }
}

// Constructor
Bus::Bus(const string& name) : Device(name) {
    // Create logs directory if it doesn't exist
    if (!filesystem::exists("logs")) {
        filesystem::create_directory("logs");
    }
    
    // Set log file path
    logFilePath = "logs/" + name + "_log.txt";
    
    // Create/clear the log file
    ofstream logFile(logFilePath);
    if (logFile.is_open()) {
        logFile << "=== Activity Log for Bus " << name << " ===" << endl;
        logFile << "Started on: " << getCurrentTimestamp() << endl;
        logFile << "===============================" << endl << endl;
        logFile.close();
    }
}

void Bus::logMessage(const string& message) {
    ofstream logFile(logFilePath, ios::app);
    if (logFile.is_open()) {
        logFile << "[" << getCurrentTimestamp() << "] " << message << endl;
        logFile.close();
    }
}

// Connect a device to the bus
void Bus::connectDevice(Device* device) {
    // Create a new connection
    Connection* connection = new Connection(this, device, connectedDevices.size(), 0);
    
    // Add the connection to this bus
    connections.push_back(connection);
    
    // Add the connection to the other device
    device->addConnection(connection);
    
    // Add device to our list
    connectedDevices.push_back(device);
    
    // Log the connection
    logMessage("Device " + device->getName() + " connected to bus");
}

// Handle incoming data
void Bus::receiveData(const string& data, int incomingPort, const string& senderName) {
    // Log that we received data
    string sourceInfo = senderName.empty() ? "unknown" : senderName;
    logMessage("RECEIVED from " + sourceInfo + " on port " + to_string(incomingPort) + ": " + data);
    
    // Forward to all devices except the source (broadcast)
    for (int i = 0; i < connectedDevices.size(); i++) {
        // Skip the device that sent the message
        if (i != incomingPort) {
            Device* device = connectedDevices[i];
            
            // Get the connection for this device
            Connection* connection = connections[i];
            int devicePort = connection->getPortNumber(device);
            
            // Forward the message with original sender info
            device->receiveData(data, devicePort, senderName);
            
            // Log the forwarding
            logMessage("FORWARDED to " + device->getName() + ": " + data);
        }
    }
}

// Buses don't send data
void Bus::sendData(const string& data) {
    logMessage("ERROR: Buses don't initiate data sending: " + data);
}

// Get log file path
string Bus::getLogFilePath() const {
    return logFilePath;
}