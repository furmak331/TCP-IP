#include "EndDevice.h"
#include "Connection.h"
#include <ctime>
#include <iomanip>
#include <filesystem>
#include <iostream>

// Helper function to get current timestamp as string
string getCurrentTimestamp() {
    time_t now = time(0);
    tm* localTime = localtime(&now);
    char buffer[80];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", localTime);
    return string(buffer);
}

// Constructor
EndDevice::EndDevice(const string& name) : Device(name) {
    // Create logs directory if it doesn't exist
    if (!filesystem::exists("logs")) {
        filesystem::create_directory("logs");
    }
    
    // Set log file path
    logFilePath = "logs/" + name + "_log.txt";
    
    // Create/clear the log file
    ofstream logFile(logFilePath);
    if (logFile.is_open()) {
        logFile << "=== Message Log for " << name << " ===" << endl;
        logFile << "Started on: " << getCurrentTimestamp() << endl;
        logFile << "===============================" << endl << endl;
        logFile.close();
    }
}

// Helper to log messages to file
void EndDevice::logMessage(const string& message) {
    ofstream logFile(logFilePath, ios::app);
    if (logFile.is_open()) {
        logFile << "[" << getCurrentTimestamp() << "] " << message << endl;
        logFile.close();
    }
}

// Handle incoming data
void EndDevice::receiveData(const string& data, int incomingPort, const string& senderName) {
    string message;
    
    if (!senderName.empty()) {
        message = "RECEIVED from " + senderName + " on port " + to_string(incomingPort) + ": " + data;
    } else {
        message = "RECEIVED on port " + to_string(incomingPort) + ": " + data;
    }
    
    // Log the message to file
    logMessage(message);
}

// Send data through all connections
void EndDevice::sendData(const string& data) {
    // Check if we have any connections
    if (connections.empty()) {
        logMessage("ERROR: No connections available to send data: " + data);
        return;
    }
    
    // Log that we're sending
    logMessage("SENDING: " + data);
    
    // Send to all connections
    for (Connection* connection : connections) {
        Device* receiver = connection->getOtherDevice(this);
        if (receiver) {
            int receiverPort = connection->getPortNumber(receiver);
            receiver->receiveData(data, receiverPort, this->name);
        }
    }
}

// Get log file path
string EndDevice::getLogFilePath() const {
    return logFilePath;
}