#include "Network.h"
#include <iostream>

int main() {
    // Create a new network
    Network network;
    
    // ------ TEST CASE 1: Direct Connection with File Storage ------
    cout << "\n===== TEST CASE 1: DIRECT CONNECTION WITH FILE STORAGE =====" << endl;
    
    // Create two end devices
    EndDevice* computer1 = network.createEndDevice("Computer1");
    EndDevice* computer2 = network.createEndDevice("Computer2");
    
    // Connect them directly
    network.connectDevices(computer1, computer2);
    
    // Show the network
    network.displayTopology();
    
    // Send test messages
    computer1->sendData("Hello from Computer1 to Computer2!");
    computer2->sendData("Hello back from Computer2!");
    computer1->sendData("How are you doing today?");
    
    // Show received messages
    computer1->showMessageHistory();
    computer2->showMessageHistory();
    
    cout << "\nMessages have been saved to Computer1_messages.txt and Computer2_messages.txt" << endl;
    
    // ------ TEST CASE 2: Hub Connection with File Storage ------
    cout << "\n===== TEST CASE 2: HUB CONNECTION WITH FILE STORAGE =====" << endl;
    
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
    
    // Send test messages
    cout << "\nSending test messages through hub..." << endl;
    pc1->sendData("Hello from PC1 to everyone!");
    pc2->sendData("PC2 responding to the group.");
    pc3->sendData("PC3 joining the conversation.");
    
    // Show received messages
    pc1->showMessageHistory();
    pc2->showMessageHistory();
    pc3->showMessageHistory();
    
    cout << "\nMessages have been saved to PC1_messages.txt, PC2_messages.txt, and PC3_messages.txt" << endl;
    
    return 0;
}