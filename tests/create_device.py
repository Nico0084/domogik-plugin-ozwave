#!/usr/bin/python
#-*- coding: utf-8 -*-create_device.py

### configuration ######################################
ENCODER = "DAIKIN"

REST_URL="http://192.168.1.195:40405"
HOST="vmdomogik0"
DEVICE_NAME="IRTrans_1"
DEVICE_PATH = "/usr/local/irtrans"
DEVICE_IP_SERVER = "localhost"
DEVICE_IP_IRTRANS = "192.168.0.175"
##################################################
DEVICE2_NAME="IRTrans_ws"
DEVICE2_IP_SERVER = "192.168.0.172"
DEVICE2_PORT_SERVER = 5590
DEVICE2_SSL = False
DEVICE2_CERTIFICATE = ""
DEVICE2_KEY =""
##################################################

from domogik.tests.common.testdevice import TestDevice
from domogik.common.utils import get_sanitized_hostname

def create_device():
    ### create the device, and if ok, get its id in device_id
    print("Creating the irtrans device...")
    td = TestDevice()
    print 'host :',  get_sanitized_hostname()
    device_id = td.create_device("plugin-irtrans.{0}".format(get_sanitized_hostname()), "test_IRTrans_Lan", "irtrans_lan.device")
    print "Device irtrans created"
    td.configure_global_parameters({"device" : DEVICE_NAME, "ir_coder" : ENCODER, "server_path" : DEVICE_PATH, "ip_server": DEVICE_IP_SERVER, "irtrans_ip": DEVICE_IP_IRTRANS})
    print "Device irtrans configured" 

    print("Creating the irwsserver device...")
    td2 = TestDevice()
    print 'host :',  get_sanitized_hostname()
    device_id = td2.create_device("plugin-irtrans.{0}".format(get_sanitized_hostname()), "test_IRTrans_WS", "irwsserver.device")
    print "Device irwsserver created"
    td2.configure_global_parameters({"device" : DEVICE2_NAME, "ir_coder" : ENCODER, "ip_server": DEVICE2_IP_SERVER, "port_server" : DEVICE2_PORT_SERVER,
                                                  "ssl_activate": DEVICE2_SSL, "ssl_certificate": DEVICE2_CERTIFICATE,  "ssl_key": DEVICE2_KEY, 
                                                  "ir_repeat": 3, "ir_tolerance": 150,  "ir_large_tolerance": 300,  "ir_max_out": 10})
    print "Device irwsserver configured" 
    
if __name__ == "__main__":
    create_device()


# TODO : recup de la config rest
# TODO : passer les parametres a la fonction
# TODO : renommer le fichier pour pouvoir importer la fonction en lib
# TODO : create generic functions for device creation and global parameters
