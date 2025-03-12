#include "headers.h"
using namespace std;

class hub{
public:
    static int hub_id;
    hub() {
        hub_id++;
        printf("Hub %d created\n", hub_id);
    }
    vector <int> connected_devices;
    void connect_device(int device_id){
        connected_devices.push_back(device_id);
    }
    /*remove func shifts all copies of device_id to separate at last and then erase function erases form the returned ptr to the end*/
    void disconnect_device(int device_id){
        connected_devices.erase(remove(connected_devices.begin(), connected_devices.end(), device_id), connected_devices.end());
    }

};



