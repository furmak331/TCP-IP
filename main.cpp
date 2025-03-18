#include "Network.h"

int main() {
    // Create a new network
    Network network;
    
    // ------ TEST CASE 1: Direct Connection ------
    cout << "\n===== TEST CASE 1: DIRECT CONNECTION =====" << endl;
    
    // Create two end devices
    EndDevice* computer1 = network.createEndDevice("Computer1");
    EndDevice* computer2 = network.createEndDevice("Computer2");
    
    // Connect them directly
    network.connectDevices(computer1, computer2);
    
    // Show the network
    network.displayTopology();
    
    // Send a test message
    computer1->sendData("Hello from Computer1 to Computer2!");
    
    // Show received messages
    computer2->showMessageHistory();
    
    
    // ------ TEST CASE 2: Hub Connection ------
    cout << "\n===== TEST CASE 2: HUB CONNECTION =====" << endl;
    
    // Create a hub
    Hub* mainHub = network.createHub("MainHub");
    
    // Create some computers
    EndDevice* pc1 = network.createEndDevice("PC1");
    EndDevice* pc2 = network.createEndDevice("PC2");
    EndDevice* pc3 = network.createEndDevice("PC3");
    
    // Connect them to the hub
    network.connectToHub(mainHub, pc1);
    network.connectToHub(mainHub, pc2);
    network.connectToHub(mainHub, pc3);
    
    // Show the network
    network.displayTopology();
    
    // Send a test message
    cout << "\nSending test message through hub..." << endl;
    pc1->sendData("Hello from PC1 to everyone!");
    
    // Show received messages
    pc2->showMessageHistory();
    pc3->showMessageHistory();
    
    return 0;
}