#!/usr/bin/python
#-*- coding: utf-8 -*-

### configuration ######################################
NETWORK_ID = "ZwaveNetwork"
DRIVER="/tmp/ttyS0"
##################################################

from domogik.tests.common.testdevice import TestDevice
from domogik.common.utils import get_sanitized_hostname

plugin =  "ozwave"

def create_device():
    ### create the device, and if ok, get its id in device_id
    print("Creating the primary controller device...")
    td = TestDevice()
    td.create_device("plugin", plugin, get_sanitized_hostname(), "test_ozw_crtl", "ozwave.primary_controller")
    td.configure_global_parameters({"networkid" : NETWORK_ID, "driver": DRIVER})
    print "Device primary controller configured"

if __name__ == "__main__":
    create_device()
