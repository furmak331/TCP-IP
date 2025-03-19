#include "Hub.h"
#include "Connection.h"
#include <ctime>
#include <iomanip>
#include <filesystem>

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
Hub::Hub(const string& name) : Device(name) {
    nextPort = 0;  // Start port numbering at 0
    
    // Create logs directory if it doesn't exist
    if (!filesystem::exists("logs")) {
        filesystem::create_directory("logs");
    }
    
    // Set log file path
    logFilePath = "logs/" + name + "_log.txt";
    
    // Create/clear the log file
    ofstream logFile(logFilePath);
    if (logFile.is_open()) {
        logFile << "=== Activity Log for Hub " << name << " ===" << endl;
        logFile << "Started on: " << getCurrentTimestamp() << endl;
        logFile << "===============================" << endl << endl;
        logFile.close();
    }
}

void Hub::logMessage(const string& message) {
    ofstream logFile(logFilePath, ios::app);
    if (logFile.is_open()) {
        logFile << "[" << getCurrentTimestamp() << "] " << message << endl;
        logFile.close();
    }
}

// Connect a device to the hub
int Hub::connectDevice(Device* device) {
    // Assign a port number
    int portNumber = nextPort++;
    
    // Create a new connection
    Connection* connection = new Connection(this, device, portNumber, 0);
    
    // Add the connection to this hub
    connections.push_back(connection);
    
    // Add the connection to the other device
    device->addConnection(connection);
    
    // Log the connection
    logMessage("Device " + device->getName() + " connected on port " + to_string(portNumber));
    
    return portNumber;
}

// Handle incoming data
void Hub::receiveData(const string& data, int incomingPort, const string& senderName) {
    // Log that we received data
    string sourceInfo = senderName.empty() ? "unknown" : senderName;
    logMessage("RECEIVED from " + sourceInfo + " on port " + to_string(incomingPort) + ": " + data);
    
    // Forward to all connections except the source (broadcast)
    for (Connection* connection : connections) {
        int portNumber = connection->getPortNumber(this);
        
        // Skip the incoming port
        if (portNumber != incomingPort) {
            Device* otherDevice = connection->getOtherDevice(this);
            if (otherDevice) {
                int otherPortNumber = connection->getPortNumber(otherDevice);
                
                // Forward the message with original sender info
                otherDevice->receiveData(data, otherPortNumber, senderName);
                
                // Log the forwarding
                logMessage("FORWARDED to " + otherDevice->getName() + " on port " + 
                           to_string(portNumber) + ": " + data);
            }
        }
    }
}

// Hubs don't send data
void Hub::sendData(const string& data) {
    logMessage("ERROR: Hubs don't initiate data sending: " + data);
}

// Get log file path
string Hub::getLogFilePath() const {
    return logFilePath;
}