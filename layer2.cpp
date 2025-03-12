#include "headers.h"
using namespace std;
class l2_device{
public:
    string mac_address;
    l2_device(){
        string x = to_string(rand( )% 100) ;
        string mac_address="00::" + x;   
    }
    vector <string> mac_table;
    void add_mac(string mac){
        mac_table.push_back(mac);
    }
   
};