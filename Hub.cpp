#include "Hub.h"
#include "Connection.h"

// Constructor
Hub::Hub(const string& name) : Device(name) {
    nextPort = 0;  // Start port numbering at 0
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
    
    return portNumber;
}

// Handle incoming data
void Hub::receiveData(const string& data, int incomingPort) {
    // Print status message
    cout << name << " received data on port " << incomingPort 
         << ", broadcasting to all other ports" << endl;
    
    // Forward to all connections except the source (broadcast)
    for (Connection* connection : connections) {
        int portNumber = connection->getPortNumber(this);
        
        // Skip the incoming port
        if (portNumber != incomingPort) {
            Device* otherDevice = connection->getOtherDevice(this);
            if (otherDevice) {
                int otherPortNumber = connection->getPortNumber(otherDevice);
                otherDevice->receiveData(data, otherPortNumber);
            }
        }
    }
}

// Hubs don't send data
void Hub::sendData(const string& data) {
    cout << "Error: Hubs don't initiate data sending" << endl;
}