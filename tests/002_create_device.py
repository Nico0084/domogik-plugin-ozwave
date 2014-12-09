#!/usr/bin/python
#-*- coding: utf-8 -*-

### configuration ######################################
NETWORK_ID = "Maison"
DRIVER="/tmp/ttyS0"
##################################################

from domogik.tests.common.testdevice import TestDevice
from domogik.common.utils import get_sanitized_hostname

plugin =  "ozwave"

def create_device():
    ### create the device, and if ok, get its id in device_id
    client_id  = "plugin-{0}.{1}".format(plugin, get_sanitized_hostname())
    print("Creating the primary controller device...")
    td = TestDevice()
    params = td.get_params(client_id, "primary.controller")
    # fill in the params
    params["device_type"] = "primary.controller"
    params["name"] = "test_ozw_crtl"
    params["reference"] = "Z-Stick2"
    params["description"] = "Z-Stick2 USB"
    for idx, val in enumerate(params['global']):
#        if params['global'][idx]['key'] == 'network_id' :  params['global'][idx]['value'] = NETWORK_ID
        if params['global'][idx]['key'] == 'driver' :  params['global'][idx]['value'] = DRIVER
    for idx, val in enumerate(params['xpl']):
        params['xpl'][idx]['value'] = NETWORK_ID
    # go and create
    td.create_device(params)
    print "Device primary controller configured"
    
if __name__ == "__main__":
    create_device()


# TODO : recup de la config rest
# TODO : passer les parametres a la fonction
# TODO : renommer le fichier pour pouvoir importer la fonction en lib
# TODO : create generic functions for device creation and global parameters
