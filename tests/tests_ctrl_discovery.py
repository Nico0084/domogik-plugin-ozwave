#!/usr/bin/python
# -*- coding: utf-8 -*-

from domogik.common.plugin import Plugin
from domogik.tests.common.plugintestcase import PluginTestCase
from domogik.tests.common.testplugin import TestPlugin
from domogik.tests.common.testdevice import TestDevice
from domogik.tests.common.testsensor import TestSensor
from domogik.common.utils import get_sanitized_hostname
from datetime import datetime
import unittest
import sys
import os
import traceback

class ZwaveCtrlTestCase(PluginTestCase):

    def test_0100_ctrl_status(self):
        """ check if all the xpl messages for an inbound call is sent
            Example :
            Sample messages :

            xpl-trig : schema:cid.basic, data:{'calltype': 'inbound', 'phone' : '0102030405'}
        """
        global devices

        address = "ctrl"
        device_id = devices[address]

        print(u"Device address = {0}".format(address))
        print(u"Device id = {0}".format(device_id))
        print(u"Check that the value of controller status has been inserted in database")
        sensor = TestSensor(device_id, "ctrl-status")
        self.assertTrue(sensor.get_last_value()[1] == 'alive')


if __name__ == "__main__":

    test_folder = os.path.dirname(os.path.realpath(__file__))

    ### global variables
    # the key will be the device address
    create_devices = { "ctrl" : {
            "networkid" : "ZwaveNetwork",
            "driver": "/tmp/ttyS0"
            }
    }

    ### configuration

    # set up the xpl features
    plugin = Plugin(name = 'test',
                       daemonize = False,
                       parser = None,
                       test  = True)

    # set up the plugin name
    name = "ozwave"

    # set up the configuration of the plugin
    # configuration is done in test_0010_configure_the_plugin with the cfg content
    # notice that the old configuration is deleted before
    cfg = { 'configured' : True,
                'autoconfpath': "Y",
                'configpath': "",
                'cpltmsg': "Y",
                'ozwlog': "Y"
            }

    # specific configuration for test mdode (handled by the manager for plugin startup)
    cfg['test_mode'] = True
    cfg['test_option'] = "" # "{0}/data.json".format(test_folder)

    ### start tests

    # load the test devices class
    td = TestDevice()

    # delete existing devices for this plugin on this host
    client_id = "{0}-{1}.{2}".format("plugin", name, get_sanitized_hostname())
    try:
        td.del_devices_by_client(client_id)
    except:
        print(u"Error while deleting all the test device for the client id '{0}' : {1}".format(client_id, traceback.format_exc()))
        sys.exit(1)

    # create a test device
    devices = {}

    try:
        params = td.get_params(client_id, "ozwave.primary_controller")
        print params
        for key, dev, in create_devices.iteritems():
            # fill in the params
            params["device_type"] = "ozwave.primary_controller"
            params["name"] = "test_device_ctrlozwave_{0}".format(key)
            params["reference"] = "reference"
            params["description"] = "description"
            # global params
            for the_param in params['global']:
                if the_param['key'] == "networkid":
                    the_param['value'] = dev['networkid']
                if the_param['key'] == "driver":
                    the_param['value'] = dev['driver']
            # xpl params
            pass # there are no xpl params for this plugin
            # create
            print params
            device_id = td.create_device(params)['id']
            devices[key] = device_id

    except:
        print(u"Error while creating the test devices : {0}".format(traceback.format_exc()))
        sys.exit(1)


    ### prepare and run the test suite
    suite = unittest.TestSuite()
    # check domogik is running, configure the plugin
    suite.addTest(CallerIdTestCase("test_0001_domogik_is_running", xpl_plugin, name, cfg))
    suite.addTest(CallerIdTestCase("test_0010_configure_the_plugin", xpl_plugin, name, cfg))

    # start the plugin
    suite.addTest(CallerIdTestCase("test_0050_start_the_plugin", xpl_plugin, name, cfg))

    # do the specific plugin tests
    suite.addTest(CallerIdTestCase("test_0100_ctrl_status", xpl_plugin, name, cfg))

    # do some tests comon to all the plugins
    #suite.addTest(CallerIdTestCase("test_9900_hbeat", xpl_plugin, name, cfg))
    suite.addTest(CallerIdTestCase("test_9990_stop_the_plugin", xpl_plugin, name, cfg))

    # quit
    res = unittest.TextTestRunner().run(suite)
    if res.wasSuccessful() == True:
        rc = 0   # tests are ok so the shell return code is 0
    else:
        rc = 1   # tests are ok so the shell return code is != 0
    xpl_plugin.force_leave(return_code = rc)
