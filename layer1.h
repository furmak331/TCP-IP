#ifndef LAYER1_H
#define LAYER1_H

#include "common.h"
#include "ethernet.h"

// Physical layer device - Hub
class hub {
private:
    std::vector<int> connected_devices;

public:
    static int hub_id;
    int my_id;
    
    hub();
    
    void connect_device(int device_id);
    void disconnect_device(int device_id);
    void broadcast_frame(const EthernetFrame& frame, int sender_id);
    
    const std::vector<int>& get_connected_devices() const;
};

#endif // LAYER1_H