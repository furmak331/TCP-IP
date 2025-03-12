
#include "headers.h"
#include <fstream>
#include "layer1.cpp"
#include "layer2.cpp"
using namespace std;
class device: public l2_device{
    static int device_id;
    device(){
        device_id++;
        printf("Device %d created\n", device_id);
        ofstream file("device" + to_string(device_id) + ".txt");
        if (file.is_open()) {
            file.close();
        } else {
            cerr << "Unable to create device %d file\n", device_id;
        }
    }
 
    
};