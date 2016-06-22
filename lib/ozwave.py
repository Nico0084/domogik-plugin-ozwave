# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}$

License
======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
===========

Support Z-wave technology
Version for domogik >= 0.5

Implements
========

- Zwave

@author: Nico <nico84dev@gmail.com>
@copyright: (C) 2007-2016 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

from domogik.common.database import DbHelper
from domogikmq.reqrep.client import MQSyncReq
from domogikmq.message import MQMessage

import threading
import libopenzwave
from libopenzwave import PyManager
from ozwvalue import ZWaveValueNode
from ozwnode import ZWaveNode
from ozwctrl import ZWaveController
from ozwxmlfiles import *
from ozwmonitornodes import ManageMonitorNodes
from ozwdefs import *
from datetime import timedelta
import pwd
from copy import deepcopy
import sys
import resource
import traceback
import tailer
import re
import os
import time
import json

class OZwaveManagerException(OZwaveException):
    """"Zwave Manager exception  class"""

    def __init__(self, value):
        OZwaveException.__init__(self, value)
        self.msg = "OZwave Manager exception:"

class OZWavemanager():
    """
    ZWave class manager
    """

    def __init__(self, plugin, cb_send_sensor, stop, log, configPath, userPath, ozwlog = False):
        """ Open Plugin manager
            @ param plugin : Plugin domogik object"
            @ param cb_send_sensor : callback for sending sensor value to MQ
            @ param stop : Stop event plugin
            @ param log : instance domogik log
            @ param configPath : Access directory to openszwave library configuration (default = "./../plugins/configPath/")
            @ param userPath : Access directory to save openzwave config and log."
            @ param ozwlog (optionnal) : enable openzawe log, file OZW_Log.txt in user directory (default = "--logging false")
        """
        self._plugin = plugin
        self._device = None
        self.monitorNodes = None
        self.options = None
        self._manager = None
        self._db = DbHelper()
        self._log = log
        self._cb_send_sensor = cb_send_sensor
        self._stop = stop
        self.pluginVers = self._plugin.json_data['identity']['version']
        self._nodes = dict()
        self._pyOzwlibVersion =  'Unknown'
        self._configPath = configPath
        self._userPath = userPath
        self.lastTest = 0
        self._devicesCtrl = []
        self._openingDriver = ""
        self._completMsg = self._plugin.get_config('cpltmsg')
        self._dataTypes = []
        self.linkedLabels = []
        self._device = self._plugin.get_config('device')
        autoPath = self._plugin.get_config('autoconfpath')
        user = pwd.getpwuid(os.getuid())[0]
        self._plugin.publishMsg('ozwave.manager.state', self.getManagerInfo())
        self._plugin.publishMsg('ozwave.lib.state', self.getOpenzwaveInfo())
        # Define config path for openzwave lib
        if autoPath :
            self._configPath = libopenzwave.configPath()
            if self._configPath is None :
                self._log.warning(u"libopenzwave can't autoconfigure path to config, try python path.")
                self._configPath = os.path.abspath(libopenzwave.__file__) + "/config"
                if not self._configPath or not os.path.exists(self._configPath) :
                    self._log.warning(u"Python can't autoconfigure path to config, try user config : {0}".format(configPath))
                    self._configPath = configPath
        self._configPath = str(self._configPath)# force str type for python openzwave lib
        if not os.path.exists(self._configPath) :
            self._log.error(u"Directory openzwave config not exist : %s" , self._configPath)
            self._plugin.force_leave()
            raise OZwaveManagerException (u"Directory openzwave config not exist : %s"  % self._configPath)
        elif not os.access(self._configPath, os.R_OK) :
            self._log.error(u"User %s haven't write access on openzwave directory : %s"  %(user,  self._configPath))
            raise OZwaveManagerException ("User %s haven't write access on openzwave directory : %s"  %(user,  self._configPath))
        if not os.path.exists(self._userPath) :
            self._log.info(u"Directory openzwave user not exist, trying create : %s" , self._userPath)
            try :
                os.mkdir(self._userPath)
                self._log.info(u"User openzwave directory created : %s"  %self._userPath)
            except Exception as e:
                self._log.error(e.message)
                raise OZwaveManagerException ("User directory openzwave not exist : %s"  % self._userPath)
        if not os.access(self._userPath, os.W_OK) :
            self._log.error("User %s haven't write access on user openzwave directory : %s"  %(user,  self._userPath))
            raise OZwaveManagerException ("User %s haven't write access on user openzwave directory : %s"  %(user,  self._userPath))
        self._log.debug(u"Setting openzwave path for user : {0}".format(user))
        self._log.debug(u"     - Config path : {0}".format(self._configPath))
        self._log.debug(u"     - User path : {0}".format(self._userPath))
        # openzwave lib initialiation process
        opt = ""
        self._ozwLog = ozwlog
        opts = "--logging true" if self._ozwLog else "--logging false"
        self._log.info(u"Try to run openzwave manager")
        self.options = libopenzwave.PyOptions(config_path =str(self._configPath), user_path=str(self._userPath))
        self.options.create(self._configPath, self._userPath, opts)
        if self._completMsg: self.options.addOptionBool('NotifyTransactions',  self._completMsg)
        self.options.lock() # Needed to lock openzwave options et autorize PyManager dtarting
        self._plugin.publishMsg('ozwave.lib.state', self.getOpenzwaveInfo())
        self._configPath = self.options.getOption('ConfigPath')  # Get real path through openzwave lib
        self._userPath = self.options.getOption('UserPath')        # Get real path through openzwave lib
        self._manager = libopenzwave.PyManager()
        self._manager.create()
        self._registerOZWWatcher = False
#        self._manager.addWatcher(self.cb_openzwave) # ajout d'un callback pour les notifications en provenance d'OZW.
        self._log.info(u" {0} -- plugin version : {1}".format(self.pyOZWLibVersion, self.pluginVers))
        self._log.info(u"   - Openzwave Config path : {0}".format(self._configPath))
        self._log.info(u"   - Openzwave User path : {0}".format(self._userPath))
        self._log.debug(u"   - Openzwave options : ")
        for opt in libopenzwave.PyOptionList.keys(): self._log.debug(u"       - {0} : {1}".format(opt, self.options.getOption(opt)))
        self._plugin.publishMsg('ozwave.lib.state', self.getOpenzwaveInfo())
        self.getDeviceClasses()
        self.getManufacturers()
        self._plugin.add_stop_cb(self.stop)
        # get the data_types
        self._loadDataType()
        # create DomogikLabelAvailable list from json
        self.InitDomogikLabelAvailable()
        # get the devices list
        self.refreshDevices()
        for a_device in self._plugin.devices:
            self.addDeviceCtrl(a_device)
        if not self._devicesCtrl :
            self._log.warning(u"No device ozwave.primary_controller created in domogik, can't start openzwave driver.")
        self.starter = threading.Thread(None, self.startServices, "th_Start_Ozwave_Services", (), {})

    device = property(lambda self: self._device)
    nodes = property(lambda self: self._nodes)
    totalNodeCount = property(lambda self: len(self._nodes))
    totalSleepingNodeCount = property(lambda self: self._getTotalSleepingNodeCount())
    totalNodeCountDescription = property(lambda self: self._getTotalNodeCountDescription())
    isReady = property(lambda self: self._getIfOperationsReady())
    isInitFully = property(lambda self: self._getIsInitFully())
    pyOZWLibVersion = property(lambda self: self._getPyOZWLibVersion())

    def on_MQ_Message(self, msgid, content):
        """Handle pub message from MQ"""
        print u"New pub message {0}, {1}".format(msgid, content)
        if msgid == "device.update":
            self._log.debug(u"New pub message {0}, {1}".format(msgid, content))
            self.threadingRefreshDevices()

    def udpate_device_param(self, paramId, key=None, value=None):
        """Call DBHelper to update static device parameter"""
        with self._db.session_scope():
            config = self._db.udpate_device_param(paramId, key, value)
            self._log.debug(u"Setting global device parameter {0}, key {1} on value {2}".format(paramId, key, value))
            if config is not None:
                self.threadingRefreshDevices()

    def threadingRefreshDevices(self, max_attempt = 2):
        """Call get_device_list from MQ
            could take long time, run in thread to get free process"""
        threading.Thread(None, self.refreshDevices, "th_refreshDevices", (), {"max_attempt": max_attempt}).start()

    def refreshDevices(self, max_attempt = 2):
        devices = self._plugin.get_device_list(quit_if_no_device = False, max_attempt = 2)
        print devices
        if devices :
            self._plugin.devices = devices
            self._plugin.publishMsg('ozwave.manager.refreshdeviceslist', {'error': ""})
            for node in self._nodes.itervalues():
                node.refreshAllDmgDevice()
        else :
            self._log.error(u"Can't retrieve the device list, MQ no response, try again or restart plugin.")
            self._plugin.publishMsg('ozwave.manager.refreshdeviceslist', {'error': "Can't retrieve the device list after {0} attempt".format(max_attempt)})

    def _getIfOperationsReady(self):
        """"Return True if all conditions are ok to do openzwave actions.
            Rule : at least one controller is ready with his registered node, not necassary in _initFully state."""
        ready = False
        for ctrl in self._devicesCtrl:
            if ctrl.ready and ctrl.node is not None :
                ready = True
                break
        return ready

    def _getIsInitFully(self):
        """"Return True if all register controller are init fully."""
        fully = False
        for ctrl in self._devicesCtrl:
            if ctrl.initFully and ctrl.node is not None :
                fully = True
                break
        return fully

    def startServices(self):
        """Start all services (monitorNodes, Zwave controllers.
            Call in thread at end of pluginmanager init to avoid long domogik plugin object locked in init."""
        self._log.info("Start Ozwave services in 100ms...")
        self._stop.wait(0.1) # wait for pluginmanager finish starting.
        self.monitorNodes = ManageMonitorNodes(self)
        self.monitorNodes.start()  # Start supervising nodes activity to helper log.
        self._plugin.publishMsg('ozwave.manager.state', self.getManagerInfo())
        # Open zwave primary controllers
        while not self._devicesCtrl and not self._stop.isSet(): # no domogik device ctrl find, so try to reload devices
            self._stop.wait(5)
            if not self._stop.isSet():
                self.refreshDevices(1)
                for a_device in self._plugin.devices:
                    self.addDeviceCtrl(a_device)
        if self._devicesCtrl :
            thOpen = threading.Thread(None, self.startOpenDevicesCtrl, "th_Start_open_drivers", (), {})
            thOpen.start()
            self._plugin.register_thread(thOpen)

    def startOpenDevicesCtrl(self):
        """Start all driver with a waiting end of previous driver start treatement.
              (This is necassary because openzwave not return the driver id on notifications)
           Call in thread at end of pluginmanager init to avoid long domogik plugin object locked in init."""
        for device in self._devicesCtrl:
            while self._openingDriver and not self._stop.isSet(): self._stop.wait(0.1)
            self.openDeviceCtrl(device)
        self._plugin.publishMsg('ozwave.manager.state', self.getManagerInfo())

    def _loadDataType(self):
        mq_client  = MQSyncReq(self._plugin.zmq)
        msg = MQMessage()
        msg.set_action('datatype.get')
        result = mq_client.request('manager', msg.get(), timeout=10)
        if result :
            self._dataTypes = result.get_data()['datatypes']
            self._log.info(u"data_types list loaded.")
        else :
            self._log.warning(u"Error on retreive data_types list from MQ.")

    def getDataType(self, name):
        """Return Datatype dict corresponding to name """
        if self._dataTypes == [] : self._loadDataType()
        for dT in self._dataTypes :
            if dT == name : return self._dataTypes[dT]
        return {}

    def getCmdClassLabelConversions(self, cmdClss, label):
        """Load file lib/cmd_class_conversion.json and return possible values for a label of  commandclass."""
        json_file = "{0}/cmd_class_conversion.json".format(self._plugin.get_lib_directory())
        cmdClasses = json.load(open(json_file))
        label = label.lower()
        for cmdC, labels in cmdClasses.iteritems() :
            if cmdC == cmdClss :
                for l, values in labels.iteritems() :
                    if l.lower() == label :
                        return values
        return {}

    def InitDomogikLabelAvailable(self):
        # Add additionnal openzwave labels
        json_file = "{0}/linkedlabels.json".format(self._plugin.get_lib_directory())
        linkedLabels = json.load(open(json_file))
        self.linkedLabels = {}
        for label, links in linkedLabels.iteritems() :
            links.append(label)
            self.linkedLabels[label.lower()] = [l.lower() for l in links]
        print self.linkedLabels
        for sensor in self._plugin.json_data['sensors']:
            if self._plugin.json_data['sensors'][sensor]['name'].lower() not in DomogikLabelAvailable :
                DomogikLabelAvailable.append(self._plugin.json_data['sensors'][sensor]['name'].lower())
        for cmd in self._plugin.json_data['commands']:
            for param in self._plugin.json_data['commands'][cmd]['parameters']:
                if param['key'].lower() not in DomogikLabelAvailable :
                    DomogikLabelAvailable.append(param['key'].lower())
        self._log.info(u"Domogik label available list initialized with {0} labels.".format(len(DomogikLabelAvailable)))
        self._log.debug(u"  -- list in lower case : {0}".format(DomogikLabelAvailable))

    def getSensorByName(self, name):
        """Return the sensor(s) set in json corresponding to name """
        sensors = {}
        name = name.lower()
        print "Retrieve sensor name : {0}".format(name)
        for sensor in self._plugin.json_data['sensors']:
            if self._plugin.json_data['sensors'][sensor]['name'].lower() == name :
#                print "    Find sensor : {0}".format(self._plugin.json_data['sensors'][sensor])
                sensors[sensor] = self._plugin.json_data['sensors'][sensor]
        return sensors

    def getCommandByName(self, name):
        """Return the command(s) set in json corresponding to name """
        cmds = {}
        name = name.lower()
        print "Retrieve command name : {0}".format(name)
        for cmd in self._plugin.json_data['commands']:
            for param in self._plugin.json_data['commands'][cmd]['parameters']:
                if param['key'].lower() == name :
#                    print "    Find command : {0}".format(self._plugin.json_data['commands'][cmd])
                    cmds[cmd] = self._plugin.json_data['commands'][cmd]
        return cmds

    def findDeviceTypes(self, likelyDevices):
        """Search if device_type correspond to likely devices and return them."""
        retval = {}
        if likelyDevices :
            for id, dev_type in self._plugin.json_data['device_types'].items():
                for refDev in likelyDevices :
#                    print "   Validate likely device_type of {0} for {1}".format(id, refDev)
                    sensorsOK = False
                    cmdsOK = False
                    if likelyDevices[refDev]['listSensors'] :
                        for n in likelyDevices[refDev]['listSensors'] :
#                            print "       for n <{0}> compare sensor {1} / {2}".format(n, likelyDevices[refDev]['listSensors'][n], dev_type['sensors'])
                            if len(likelyDevices[refDev]['listSensors'][n]) == len(dev_type['sensors']) and \
                                    all(i in dev_type['sensors'] for i in likelyDevices[refDev]['listSensors'][n]):
                                sensorsOK = True
#                                print "    Sensor(s) OK"
                    else :
                        if not dev_type['sensors'] :
                            sensorsOK = True
#                            print "    Sensor(s) OK (No sensor)"
                    if likelyDevices[refDev]['listCmds'] :
                        for nc in likelyDevices[refDev]['listCmds'] :
#                            print "       for n <{0}> compare command {1} / {2}".format(nc, likelyDevices[refDev]['listCmds'][nc], dev_type['commands'])
                            if len(likelyDevices[refDev]['listCmds'][nc]) == len(dev_type['commands']) and \
                                    all(i in dev_type['commands'] for i in likelyDevices[refDev]['listCmds'][nc]):
                                cmdsOK = True
#                                print "    Command(s) OK"
                    else :
                        if not dev_type['commands'] :
                            cmdsOK = True
#                            print "    Command(s) OK (no command)"
                    if sensorsOK and cmdsOK :
                        try :
                           len(retval[refDev])
                        except :
                            retval[refDev] = []
                        retval[refDev].append(id)
        return retval

    def registerDetectedDevice(self, likelyDevices):
        """Call device_detected"""
        for refDev in likelyDevices :
            for devType in likelyDevices[refDev] :
                print "Try to register device {0}.{1}.{2}, {3}".format(refDev[0], refDev[1], refDev[2], devType)
                globalP = [{
                            "key" : "networkid",
                            "value": u"{0}".format(refDev[0])
                        }, {
                            "key" : "node",
                            "value": u"{0}".format(refDev[1])
                        }, {
                            "key" : "instance",
                            "value": u"{0}".format(refDev[2])
                        }]
                self._plugin.device_detected({
                    "device_type" : devType,
                    "reference" : "",
                    "global" : globalP,
                    "xpl" : [],
                    "xpl_commands" : {},
                    "xpl_stats" : {}
                })

    def _setNew_Device_Type(self, devType, id, sensors, cmds):
        """Set values for a new device_type."""
        batteryParam = {
            u"key" : u"batterycheck",
            u"xpl": False,
            u"description" : u"Check battery level at zwave device wakeup.",
            u"type" : u"boolean"
        }
        devType["sensors"] = sensors
        devType["commands"] = cmds
        devType["id"] = id
        if "battery-level" in sensors : devType["parameters"].append(batteryParam)
        return devType

    def create_Device_Type_Feature(self, likelyDevices):
        """Return list of device_type id formated by rule "ozwave.<'-'.join(sensor list)'__''-'.join(command list)"""
        devTypes = {}
        device_type_Model = {
            u"description" : u"Zwave device information, Must be edited",
            u"id": "",
            u"name" : u"Device type name, Must be edited",
            u"commands": [],
            u"sensors": [""],
            u"parameters" : [{
                u"key" : u"networkid",
                u"xpl": False,
                u"description" : u"Zwave network name if refered in controller node or Openzwave Home ID",
                u"type" : u"string"
            },{
                u"key" : u"node",
                u"xpl": False,
                u"description" : u"Zwave node id",
                u"type" : u"integer",
                u"max_value": 255,
                u"min_value": 1
            },{
                u"key" : u"instance",
                u"xpl": False,
                u"description" : u"Zwave node instance id",
                u"type" : u"integer",
                u"max_value": 255,
                u"min_value": 1
            }]
        }
        for refDev in likelyDevices :
            if likelyDevices[refDev]["listSensors"] != {} :
                for s in likelyDevices[refDev]["listSensors"] :
                    sensors = list(likelyDevices[refDev]["listSensors"][s])
                    if sensors :
                        sensors.sort()
                        sName = "_".join(sensors)
                    else : sName = ""
                    if likelyDevices[refDev]["listCmds"] != {} :
                        for c in likelyDevices[refDev]["listCmds"] :
                            cmds = list(likelyDevices[refDev]["listCmds"][c])
                            if cmds :
                                cmds.sort()
                                cName = u"__{0}".format("_".join(cmds))
                                id = u"ozwave.{0}{1}".format(sName, cName)
                                if id not in self._plugin.json_data['device_types'].keys():
                                    devTypes[id] = self._setNew_Device_Type(deepcopy(device_type_Model), id, sensors, cmds)
                                    print "ADD 1 : {0}".format(devTypes[id])
                    else :
                        id = u"ozwave.{0}".format(sName)
                        if id not in self._plugin.json_data['device_types'].keys():
                            devTypes[id] = self._setNew_Device_Type(deepcopy(device_type_Model), id, sensors, [])
                            print "ADD 2 : {0}".format(devTypes[id])
            else :
                for c in likelyDevices[refDev]["listCmds"] :
                    cmds = list(likelyDevices[refDev]["listCmds"][c])
                    if cmds :
                        cmds.sort()
                        cName = u"__{0}".format("_".join(cmds))
                        id = u"ozwave.{0}".format(cName)
                        if id not in self._plugin.json_data['device_types'].keys():
                            devTypes[id] = self._setNew_Device_Type(deepcopy(device_type_Model), id, [], cmds)
                            print "ADD 3 : {0}".format(devTypes[id])
        return devTypes

    def getDeviceCtrl(self, key, value ):
        """Retourne le device ctrl de type primary.controler.
            @params key : <'driver', 'networkID',  'homeID', 'node'>
            @params value : value dépendante de key
        """
        for device in self._devicesCtrl :
            if key == 'driver' and device.driver == value : return device
            elif key == 'networkID' and device.networkID == value : return device
            elif key == 'homeID' and self.matchHomeID(device.homeId) == self.matchHomeID(value) : return device
            elif key == 'node' and device.node == value : return device
        return None

    def addDeviceCtrl(self, dmgDevice):
        if dmgDevice['device_type_id'] == 'ozwave.primary_controller' :
            driver = str(self._plugin.get_parameter(dmgDevice, 'driver')) # force str type for python openzwave lib
            if not self.getDeviceCtrl('driver', driver) :
                networkID = self._plugin.get_parameter(dmgDevice, 'networkid')
                self._devicesCtrl.append(PrimaryController(self, driver, networkID, None))
                self._log.info(u"Domogik device primary controller registered : {0}".format(self._devicesCtrl[-1]))
            else : self._log.info("Device primary controller allready exist on {0}".format(driver))

    def removeDeviceCtrl(self, device):
       if device in self._devicesCtrl :
           self.closeDeviceCtrl(device)
           self._log.info(u"Domogik device primary controller disconnected from openzwave : {0}".format(device))
#           self._devicesCtrl.remove(device)

    def isNodeDeviceCtrl(self,  node):
        """Return le deviceCtrl si le node est un controleur primaire sinon None."""
        for device in self._devicesCtrl :
            if node == device.node : return device
        return None

    def sendDmgCtrlStatus(self, ctrl, status):
        for a_device in self._plugin.devices:
            if a_device['device_type_id'] == 'ozwave.primary_controller' and ctrl.networkID == self._plugin.get_parameter(a_device, 'networkid'):
                self._cb_send_sensor({'networkid': ctrl.networkID,  'node': ctrl.nodeId},
                                                      a_device['sensors']['ctrl-status']['id'], a_device['sensors']['ctrl-status']['data_type'], status['status'])
                break

    def matchHomeID(self, homeId):
        """Evalue si c'est bien un homeID, retourne le homeID ou None"""
        if type(homeId) in [long,  int] :
            return "0x%0.8x" %homeId
        homeIDFormat = r"^0x[0-9,a-f]{8}$"
        if type(homeId) == str :
            if re.match(homeIDFormat,  homeId.lower()) is not None :
                return homeId.lower()
        return None

    def getCtrlOfNode(self, node):
        """Retourne le controleur d'un node."""
        for ctrlNode in self._devicesCtrl:
            if ctrlNode.homeId == node.homeId : return ctrlNode
        return None

    def getCtrlOfNetwork(self, networkID):
        """Retourne le controleur d'un reseaux zwave."""
        homeId = self.matchHomeID(networkID)
        if homeId is not None :
            homeId = long(homeId, 16)
            for ctrlNode in self._devicesCtrl:
                if ctrlNode.homeId == homeId: return ctrlNode
        else :
            for ctrlNode in self._devicesCtrl:
                if ctrlNode.networkID == networkID: return ctrlNode
        return None

    def getNetworkID(self, id):
        """Retourne le networkID  correspondant à id, peux être le homeID si le networkID n'est pas renseigné. None si le networkID n'existe pas."""
        homeID = self.matchHomeID(id)
        if homeID is not None :
            for ctrlNode in self._devicesCtrl:
                if self.matchHomeID(ctrlNode.homeId) == homeID : return ctrlNode.networkID
        else :
            for ctrlNode in self._devicesCtrl:
                if ctrlNode.networkID == id : return ctrlNode.networkID
        self._log.warning(u"NetworkID or homeID doesn't exist : {0}".format(id))
        return None

    def getHomeID(self,  id):
        """Retourne le homeId correspondant à id ou None si pas trouvé."""
        homeID = self.matchHomeID(id)
        if homeID is not None :
            return homeID
        else :
            for ctrlNode in self._devicesCtrl:
                if ctrlNode.networkID == id : return self.matchHomeID(ctrlNode.homeId)
        self._log.warning(u"NetworkID or homeID doesn't exist : {0}".format(id))
        return None

    def openDeviceCtrl(self, ctrl):
        """Open openzwave controller."""
        if ctrl.status == 'open':
            self._log.warning(u"Driver {0} allready open. Can't reopen it.".format(ctrl.driver))
        else :
            if not self._registerOZWWatcher :
#                TODO: For now only one watcher for all potential driver.  Must be implemented with one watcher per driver.
                self._log.info(u"Adding notification OZW watcher for driver : {0}".format(ctrl.driver))
                self._manager.addWatcher(self.cb_openzwave)
                self._registerOZWWatcher = True
            self._log.info(u"Adding driver to openzwave : {0}".format(ctrl.driver))
            self._plugin.publishMsg('ozwave.ctrl.opening', {'NetworkID': ctrl.networkID, 'Driver': ctrl.driver})
            self._manager.addDriver(ctrl.driver)  # Add driver in driver manager list
            ctrl.status = 'open'
            self._openingDriver = ctrl.driver

    def closeDeviceCtrl(self, ctrl):
        """Close openzwave controller."""
        if ctrl.status == 'open' :
#             TODO: For now only one watcher for all potential driver.  Must be implemented with one watcher per driver.
            if self._registerOZWWatcher :
                self._log.info(u"Remove notification OZW Watcher for driver : {0}".format(ctrl.driver))
                self._registerOZWWatcher = False
                self._manager.removeWatcher(self.cb_openzwave)
            self._log.info(u"Remove driver from openzwave : {0}".format(ctrl.driver))
            if self._manager.removeDriver(ctrl.driver) :
                ctrl.setClosed()
                self._plugin.publishMsg('ozwave.ctrl.closed', {"NetworkID": ctrl.networkID, 'Driver': ctrl.driver, 'type': 'driver-remove', 'usermsg' : 'Driver removed.', 'data': False})
            else :
                self._log.error(u"Libopenzwave fail to remove openzwave driver {0}".format(ctrl.driver))

    def stop(self):
        """ Stop class OZWManager."""
        self._log.info(u"Stopping plugin, Remove driver(s) from openzwave")
        for ctrl in self._devicesCtrl : self.removeDeviceCtrl(ctrl)
        self.monitorNodes.stop()
        if self._plugin._ctrlsHBeat: self._plugin._ctrlsHBeat.stop()
        self._plugin.publishMsg('ozwave.manager.stopped',{'NetworkID': ctrl.networkID, 'NodeID': ctrl.nodeId, 'type': 'driver-remove', 'usermsg' : 'Plugin stopped.', 'data': False})

    def sendHbeatCtrlsState(self):
        """send hbeat zwave controllers state"""
        for ctrl in self._devicesCtrl:
            status = ctrl.getStatus()
            self.sendDmgCtrlStatus(ctrl, status)
            status.update({'NetworkID': ctrl.networkID, 'HomeID': self.matchHomeID(ctrl.homeId)})
            self._plugin.publishMsg('ozwave.ctrl.state', status)

    def getDeviceClasses(self):
        """"Return list of all device type classes known by openzwave lib (config/device_classes.xml)."""
        self.deviceClasses = DeviceClasses(self._configPath)

    def getManufacturers(self):
        """"Return list of all manufacturer and product known by openzwave lib (config/manufacturer_specific.xml)."""
        self.manufacturers = Manufacturers(self._configPath)

    def getAllProducts(self):
        """"Return list of all manufacturer and product known by openzwave lib."""
        if self.manufacturers :
            return {'error' : '', 'manufacturers': self.manufacturers.getAllProductsName()}
        else :
            return {'error': 'Manufacturers xml file not loaded.', 'manufacturers': []}

    def getProduct(self, productName):
        """Return all informations of a product known by openzwave lib"""
        if self.manufacturers :
            product = self.manufacturers.getProduct(productName)
            if product is not None :
                data = product.getProductData()
                for val in data['commandClasses'] :
                    val['cmdClassName'] = self.getCommandClassName(val['id'])
                return {'error' : '', 'product': data}
            else:
               return {'error': 'Product not find in xml file not loaded.', 'product': []}
        else :
            return {'error': 'Manufacturers xml file not loaded.', 'product': []}

    def _getPyOZWLibVersion(self):
        """Renvoi les versions des librairies py-openzwave ainsi que la version d'openzwave."""
        try :
            self._pyOzwlibVersion = self._manager.getPythonLibraryVersion ()
        except :
            self._pyOzwlibVersion  =  'Unknown'
            return 'py-openzwave : < 0.1 check for update, OZW revision : Unknown'
        try :
            ozwvers = self._manager.getOzwLibraryVersion ()
        except :
            ozwvers  =  'OZW revision :Unknown < r530'
        if self._pyOzwlibVersion :
            return '{0} , {1}'.format(self._pyOzwlibVersion,  ozwvers)
        else:
            return 'Unknown'

    def getLoglines(self, message):
        """Renvoi les lignes Start à End du fichier de log."""
        retval = {'error': ""}
        try :
            if 'lines' in message:
                lines = int(message['lines'])
        except :
            lines = 50
        try:
           # filename = os.path.join("/var/log/domogik/ozwave.log")
            for h in self._log.__dict__['handlers']:
                if h.__class__.__name__ in ['FileHandler', 'TimedRotatingFileHandler','RotatingFileHandler', 'WatchedFileHandler']:
                    filename = h.baseFilename

            if message['from'] == 'top':
                retval['data'] = tailer.head(open(filename), lines)
            elif message['from'] == 'end':
                retval['data'] = tailer.tail(open(filename), lines)
            else: return {'error': "No from direction define."}
        except:
                retval['error'] = "Exception : %s" % (traceback.format_exc())
                self._log.error("Get log lines : " + retval['error'])
        return retval

    def getLogOZWlines(self, message):
        """Renvoi les lignes Start à End du fichier de log d'openzwave (OZW_Log.txt)."""
        if not self._ozwLog : return {'error': "Openzwave log disable, enabled it with plugin parameter and restart plugin."}
        filename = os.path.join(self._userPath + "OZW_Log.txt")
        if not os.path.isfile(filename) : return {'error': "No existing openzwave log file : " + filename}
        retval = {'error': ""}
        try :
            if 'lines' in message:
                lines = int(message['lines'])
        except :
            lines = 50
        try:
            if message['from'] == 'top':
                retval['data'] = tailer.head(open(filename), lines)
            elif message['from'] == 'end':
                retval['data'] = tailer.tail(open(filename), lines)
            else: return {'error': "No from direction define."}
        except :
                retval['error'] = "Exception : %s" % (traceback.format_exc())
                self._log.error("Get log openzwave lines : " + retval['error'])
        return retval

    def _getTotalSleepingNodeCount(self):
        """ Renvoi le nombre total, tous controleur, de node en veille."""
        retval = 0
        for node in self._nodes.itervalues():
            if node.isSleeping:
                retval += 1
        return retval if retval > 0 else 0

    def getMemoryUsage(self):
        """Renvoi l'utilisation memoire du plugin"""
        total = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        tplugin = sys.getsizeof(self) + sum(sys.getsizeof(v) for v in self.__dict__.values()) + self._plugin.getsize()
        if self.manufacturers : tplugin += self.manufacturers.getMemoryUsage();
        for node in self._nodes.itervalues() :
            tplugin += node.getMemoryUsage()
        tplugin= tplugin/1024
        retval = {'Plugin manager with ' + str(len(self._nodes)) + ' nodes' : '%s kbytes' %  tplugin}
        retval ['Total memory use'] = '%s Mo' % (total / 1024.0)
        retval ['Openzwave'] = '%s ko' % (total - tplugin)
        return retval

    def _getTotalNodeCountDescription(self):
        """Renvoi le nombre de node total, tous controleur, et/ou le nombre en veille (return str)"""
        retval = '{0} Nodes'.format(self.totalNodeCount)
        sleepCount = self.totalSleepingNodeCount
        if sleepCount:
            retval = '{0} ({1} sleeping)'.format(retval, sleepCount)
        return retval

    def refNode(self, homeId, nodeId):
        """Retourne la reference du node pour le dict self._nodes et les messages"""
        return "{0}.{1}".format(self.getHomeID(homeId), nodeId)

    def _IsNodeId(self, nodeId):
        """Verifie le si le format de nodeId est valide"""
        return True if (type(nodeId) == type(0) and (nodeId >0 and nodeId < 255)) else False

    def _getNode(self, homeId, nodeId):
        """ Renvoi l'objet node correspondant"""
        ref = self.refNode(homeId, nodeId)
        if ref in self._nodes :
            return self._nodes[ref]
        else :
            self._log.debug("Z-Wave Device Node {0} isn't register to manager.".format(ref))
            return None

    def _fetchNode(self, homeId, nodeId):
        """ Renvoi et construit un nouveau node s'il n'existe pas et l'enregistre dans le dict """
        retval = self._getNode(homeId, nodeId)
        if retval is None:
            if nodeId != 0 :
                ref = self.refNode(homeId, nodeId)
                ctrl = self.getCtrlOfNetwork(homeId)
                if ctrl is None :
                    self._log.warning(u"A Node is added but no device primary controller created for home ID :{0}, Create it in domogik.".format(homeId))
                    ctrlNodeID = 0
                else : ctrlNodeID = ctrl.nodeID
                if nodeId == ctrlNodeID :
                    retval = ZWaveController(self,  homeId, nodeId,  True,  ctrl.networkID)
                    self._log.info(u"Node {0} is affected as primary controller".format(nodeId))
                    ctrl.node = retval
                    retval.reportChangeToUI({"NetworkID": ctrl.networkID, 'NodeID': nodeId, 'type': 'init-process', 'usermsg' : 'Zwave network initialization process could take several minutes. ' +
                                                ' Please be patient...', 'data': NodeStatusNW[3]})
                    # TODO: Voir comment gérer les controler secondaire, type ZWaveNode ou ZWaveController ?
#                            self._log.info("A primary controller allready existing, node %d id affected as secondary.", nodeId)
#                            retval = ZWaveController(self, homeId, nodeId,  False)
                else :
                    retval = ZWaveNode(self, homeId, nodeId)
                self._log.info(u'Created new node {0}'.format(ref))
                self._nodes[ref] = retval
                self._plugin.publishMsg('ozwave.ctrl.report',{'NetworkID': ctrl.networkID, 'NodeID': nodeId, 'type': 'init-process',
                                                                                      'usermsg' : 'New node added ', 'data': NodeStatusNW[0]})
            else :
                self._log.debug("Can't create a Node ID n°0")
                raise OZwaveManagerException ("Can't create a Node ID n°0")
                retval = None
        return retval

    def cb_openzwave(self,  args):
        """Callback depuis la librairie py-openzwave
        """
    # callback ordre : (notificationtype, homeId, nodeId, ValueID, groupidx, event)
    # notification implémentés
#         ValueAdded = 0                    / A new node value has been added to OpenZWave's list. These notifications occur after a node has been discovered, and details of its command classes have been received.  Each command class may generate one or more values depending on the complexity of the item being represented.
#         ValueRemoved = 1                  / A node value has been removed from OpenZWave's list.  This only occurs when a node is removed.
#         ValueChanged = 2                  / A node value has been updated from the Z-Wave network and it is different from the previous value.
#         Group = 4                         / The associations for the node have changed. The application should rebuild any group information it holds about the node.
#         NodeNew = 5                       / A new node has been found (not already stored in zwcfg*.xml file)
#         NodeAdded = 6                     / A new node has been added to OpenZWave's list.  This may be due to a device being added to the Z-Wave network, or because the application is initializing itself.
#         NodeRemoved = 7                   / A node has been removed from OpenZWave's list.  This may be due to a device being removed from the Z-Wave network, or because the application is closing.
#         NodeProtocolInfo = 8              / Basic node information has been receievd, such as whether the node is a listening device, a routing device and its baud rate and basic, generic and specific types. It is after this notification that you can call Manager::GetNodeType to obtain a label containing the device description.
#         NodeNaming = 9                    / One of the node names has changed (name, manufacturer, product).
#         NodeEvent = 10                    / A node has triggered an event.  This is commonly caused when a node sends a Basic_Set command to the controller.  The event value is stored in the notification.
#         PollingDisabled = 11              / Polling of a node has been successfully turned off by a call to Manager::DisablePoll
#         PollingEnabled = 12               / Polling of a node has been successfully turned on by a call to Manager::EnablePoll
#         DriverReady = 18                  / A driver for a PC Z-Wave controller has been added and is ready to use.  The notification will contain the controller's Home ID, which is needed to call most of the Manager methods.
#         DriverFailed = 19                 / Driver failed to load
#         EssentialNodeQueriesComplete = 21 / The queries on a node that are essential to its operation have been completed. The node can now handle incoming messages.
#         NodeQueriesComplete = 22          / All the initialisation queries on a node have been completed.
#         AwakeNodesQueried = 23            / All awake nodes have been queried, so client application can expected complete data for these nodes.
#         AllNodesQueriedSomeDead = 24      / All nodes have been queried but some dead nodes found.
#         AllNodesQueried = 25              / All nodes have been queried, so client application can expected complete data.
#         Notification = 26                        / An error has occured that we need to report.
#         DriverRemoved = 27                 / The Driver is being removed. (either due to Error or by request) Do Not Call Any Driver Relatedh -- see rev : ttps://code.google.com/p/open-zwave/source/detail?r=890
#         ControllerCommand = 28	      / When Controller Commands are executed, Notifications of Success/Failure etc are communicated via this Notification
#											    Notification::GetEvent returns Driver::ControllerCommand and Notification::GetNotification returns Driver::ControllerState

#TODO: notification à implémenter
#         ValueRefreshed = 3                / A node value has been updated from the Z-Wave network.
#         SceneEvent = 13                 / Scene Activation Set received
#         CreateButton = 14                 / Handheld controller button event created
#         DeleteButton = 15                 / Handheld controller button event deleted
#         ButtonOn = 16                     / Handheld controller button on pressed event
#         ButtonOff = 17                    / Handheld controller button off pressed event
#         DriverReset = 20                  / All nodes and values for this driver have been removed.  This is sent instead of potentially hundreds of individual node and value notifications.
#		  NodeReset = 29	        			/ The Device has been reset and thus removed from the NodeList in OZW.

        self.monitorNodes.openzwave_report(args)
        print('\n%s\n[%s]:' % ('-'*40, args['notificationType']))
        print args
        notifyType = args['notificationType']
        if notifyType == 'DriverReady':
            self._handleDriverReady(args)
        elif notifyType == 'DriverFailed':
            self._handleDriverFailed(args)
        elif notifyType in ('NodeAdded', 'NodeNew'):
            self._handleNodeChanged(args)
        elif notifyType == 'NodeRemoved':
            self._handleNodeRemoved(args)
        elif notifyType == 'ValueAdded':
            self._handleValueAdded(args)
        elif notifyType == 'ValueRemoved':
            self._handleValueRemoved(args)
        elif notifyType == 'ValueChanged':
            self._handleValueChanged(args)
        elif notifyType == 'NodeEvent':
            self._handleNodeEvent(args)
        elif notifyType == 'Group':
            self._handleGroupChanged(args)
        elif notifyType in ('AwakeNodesQueried', 'AllNodesQueried'):
            self._handleInitializationComplete(args)
        elif notifyType in ('AllNodesQueriedSomeDead'):
            self._handleMarkSomeNodesDead(args)
        elif notifyType == 'NodeProtocolInfo':
            self._handleNodeLinked(args)
        elif notifyType == 'EssentialNodeQueriesComplete':
            self._handleNodeReadyToMsg(args)
        elif notifyType == 'PollingDisabled':
            self._handlePollingDisabled(args)
        elif notifyType == 'PollingEnabled':
            self._handlePollingEnabled(args)
        elif notifyType == 'NodeNaming':
            self._handleNodeNaming(args)
        elif notifyType == 'NodeQueriesComplete':
            self._handleNodeQueryComplete(args)
        elif notifyType == 'Notification':
            self._handleNotification(args)
        elif notifyType == 'ControllerCommand':
            self._handleControllerCommand(args)
        elif notifyType == 'DriverRemoved':
            self._handleDriverRemoved(args)
        else :
            self._log.info("zwave callback : %s is not handled yet",  notifyType)
            self._log.info(args)

    def _handleDriverReady(self, args):
        """Appelé une fois que le controleur est déclaré et initialisé dans OZW.
        l'HomeID et NodeID du controleur sont enregistrés."""
        ctrl = self.getDeviceCtrl("driver",  self._openingDriver)
        if ctrl :
            ctrl.homeId = long(args['homeId']) # self.matchHomeID(args['homeId'])
            ctrl.nodeID = args['nodeId']
            ctrl.status = 'open'
            ctrl.libraryVersion = self._manager.getLibraryVersion(ctrl.homeId)
            ctrl.libraryTypeName = self._manager.getLibraryTypeName(ctrl.homeId)
            ctrl.timeStarted = time.time()
            ctrl.ready = True
            self._openingDriver = ""
            self._plugin.publishMsg('ozwave.manager.state', self.getManagerInfo())
            self._log.info(u"Driver {0} ready. homeId is {1}, controller node id is {2}, using {3} library version {4}".format(ctrl.driver,
                           self.matchHomeID(ctrl.homeId),
                           ctrl.nodeID, ctrl.libraryTypeName, ctrl.libraryVersion))
            data = {'NetworkID': ctrl.networkID, 'HomeID': self.matchHomeID(ctrl.homeId), 'type': 'change', 'value': 'driver-ready', 'usermsg' : 'Driver is ready.'}
            data.update(ctrl.getStatus())
            self.sendDmgCtrlStatus(ctrl, data)
            self._plugin.publishMsg('ozwave.ctrl.state', data)

    def _handleDriverReset(self, args):
        """ Le driver à été recu un reset, tous les nodes, sauf le controlleur, sont détruis."""
        ctrl = self.getDeviceCtrl('homeID', args['homeId']) # TODO: vérifier si args retourne le driver ou homeId
        if ctrl is not None :
            ctrl.ready = False
            ctrl.initFully = False
            for n in self._nodes:
                if (self._nodes[n] != ctrl.node) and (self._nodes[n].homeId == ctrl.homeId) :
                    node = self._nodes.pop(n)
                    del(node)
            self._log.info(u"Driver {0}, homeId {1} is reset, all network nodes deleted".format(ctrl.driver, args))
            data = {'NetworkID': ctrl.networkID, 'HomeID': self.matchHomeID(ctrl.homeId), 'type': 'change', 'value': 'driver-reset', 'usermsg' : 'Driver reseted, All nodes must be recovered.'}
            data.update(ctrl.getStatus())
            self.sendDmgCtrlStatus(ctrl, data)
            self._plugin.publishMsg('ozwave.ctrl.state', data)
        else :
            self._log.warning(u"A driver reset is recieved but not domogik controller attached, all nodes deleted. Notification : {1}".format(args))
            self._plugin.publishMsg('ozwave.ctrl.state', {'NetworkID': ctrl.networkID, 'NodeID': ctrl.nodeId, 'type': 'change', 'value': 'driver-reset', 'usermsg' : 'Driver reseted but not registered, All nodes must be recovered.', 'state' : 'dead', 'init': NodeStatusNW[6]})
            self._nodes = None

    def _handleDriverRemoved(self,  args):
        """ Le driver à été arrêter et supprimer, tous les nodes sont détruis."""
        ctrl = self.getDeviceCtrl('homeID', args['homeId']) # TODO: vérifier si args retourne le driver ou homeId
        if ctrl is not None :
            ctrl.ready = False
            ctrl.initFully = False
            ctrl.status = 'close'
            delN = [refNode for refNode, node in self._nodes.iteritems() if node.homeId == ctrl.homeId]
            for refNode in delN:
                del self._nodes[refNode]
            self._log.info(u"Driver {0}, homeId {1} is removed, all network nodes deleted".format(ctrl.driver, args))
            data = {'NetworkID': ctrl.networkID, 'HomeID': self.matchHomeID(ctrl.homeId), 'type': 'change', 'value': 'driver-remove', 'usermsg' : 'Driver removed, All nodes deleted.'}
            data.update(ctrl.getStatus())
            self.sendDmgCtrlStatus(ctrl, data)
            self._plugin.publishMsg('ozwave.ctrl.state', data)
        else :
            self._log.warning(u"A driver removed is recieved but not domogik controller attached, all nodes deleted. Notification : {1}".format(args))
            self._plugin.publishMsg('ozwave.ctrl.state', {'NetworkID': ctrl.networkID, 'NodeID': ctrl.nodeId, 'type': 'change', 'value': 'driver-remove', 'usermsg' : 'Driver removed but not registered, All nodes deleted.', 'state' : 'dead', 'init': NodeStatusNW[6]})
            self._devicesCtrl = None
            self._nodes = None

    def _handleDriverFailed(self, args):
        """L'ouverture du driver à échoué.."""
        ctrl = self.getDeviceCtrl('driver', self._openingDriver)
        self._openingDriver = ""
        ctrl.status = 'fail'
        ctrl.ready = False
        ctrl.initFully = False
        self._log.error(u"Openzwave fail to open driver {0}, ozw message : {1}".format(ctrl.driver, args))
        data = {'NetworkID': ctrl.networkID, 'HomeID': self.matchHomeID(ctrl.homeId), 'type': 'change', 'value': 'driver-failed', 'usermsg' : 'Openzwave opening driver {0} fail.'.format(ctrl.driver)}
        data.update(ctrl.getStatus())
        self.sendDmgCtrlStatus(ctrl, data)
        self._plugin.publishMsg('ozwave.ctrl.state', data)

    def _handleInitializationComplete(self, args):
        """La séquence d'initialisation du controleur zwave est terminée."""
        self._log.debug(u"Starting process initialization complete requested by {0}".format(args['notificationType']))
        controllercaps = set()
        ctrl = self.getDeviceCtrl("homeID",  args['homeId'])
        if self._manager.isPrimaryController(ctrl.homeId): controllercaps.add('Primary Controller')
        if self._manager.isStaticUpdateController(ctrl.homeId): controllercaps.add('Static Update Controller')
        if self._manager.isBridgeController(ctrl.homeId): controllercaps.add('Bridge Controller')
        ctrl.controllerCaps = controllercaps
        self._log.info(u"Controller capabilities are: {0}".format(controllercaps))
        for node in self._nodes.itervalues():
            self._log.debug(u"     In process initialization complete, refresh node {0} informations.".format(node.nodeId))
            node.updateNode() # Pourrait être utile si un node s'est réveillé pendant l'init.
            if not node.isConfigured :
                node.updateConfig()
        self._log.debug(u"End of process initialization complete")
        ctrl.ready = True
        ctrl.initFully = True
        data = {'NetworkID': ctrl.networkID, 'HomeID': self.matchHomeID(ctrl.homeId), 'type': 'change', 'value': 'driver-init', 'usermsg' :'Zwave network Initialized.'}
        data.update(ctrl.getStatus())
        self.sendDmgCtrlStatus(ctrl, data)
        self._plugin.publishMsg('ozwave.ctrl.state', data)
        self._log.info("OpenZWave initialization completed for driver {0}. Found {1} Z-Wave Device Nodes ({2} sleeping, {3} Dead)".format(ctrl.driver, ctrl.getNodeCount(), ctrl.getSleepingNodeCount(), ctrl.getFailedNodeCount()))

    def _handleNodeLinked(self, args):
        """Le node est relier au controleur."""
        node = self._getNode(args['homeId'], args['nodeId'])
        if node :
            node.setLinked()
            self._log.info('Z-Wave Device Node {0} is linked to controller.'.format(node.refName))
        else :
            self._log.debug('Error notification : ', args)

    def _handleNodeReadyToMsg(self, args):
        """Les requettes essentielles d'initialisation du node sont complétée il peut recevoir des msg."""
        node = self._getNode(args['homeId'], args['nodeId'])
        if node :
            node.setReceiver()
            self._log.info('Z-Wave Device Node {0} status essential queries ok.'.format(node.refName))
            ctrl = self.isNodeDeviceCtrl(node)
            if ctrl and not ctrl.ready :
                ctrl.ready = True
                self._log.info('Z-Wave Controller Node {0} is ready, UI dialogue autorised.'.format(node.refName))
        else :
            self._log.debug('Error notification : ', args)

    def _handleNodeNaming(self, args):
        """Le node à été identifié dans la lib openzwave. Son fabriquant et type sont connus"""
        node = self._getNode(args['homeId'], args['nodeId'])
        if node :
            node.setNamed()
            self._log.info('Z-Wave Device Node {0} type is known in openzwave library.'.format(node.refName))
        else :
            self._log.debug('Error notification : ', args)

    def _handleNodeQueryComplete(self, args):
        """Les requettes d'initialisation du node sont complété."""
        node = self._getNode(args['homeId'], args['nodeId'])
        if node :
            node.setReady()
            node.updateNode()
            self._log.info('Z-Wave Device Node {0} is ready, full initialized.'.format(self.refNode(node.homeId, node.nodeId)))
            ctrl = self.isNodeDeviceCtrl(node)
            if ctrl and not ctrl.ready :
                ctrl.ready = True
                data = {'NetworkID': ctrl.networkID, 'HomeID': self.matchHomeID(ctrl.homeId), 'type': 'change', 'value': 'driver-ready', 'usermsg' : 'Driver is ready.'}
                data.update(ctrl.getStatus())
                self.sendDmgCtrlStatus(ctrl, data)
                self._plugin.publishMsg('ozwave.ctrl.state', data)
                self._log.info('Z-Wave Controller Node {0} is ready, UI dialogue autorised.'.format(self.refNode(ctrl.homeId, node.nodeId)))
        else :
            if args['nodeId'] == 255 and not self.isInitFully :
                self._handleInitializationComplete(args) # TODO :depuis la rev 585 pas de 'AwakeNodesQueried' ou  'AllNodesQueried' ? on force l'init

    def _handleMarkSomeNodesDead(self,  args):
        """Un ou plusieurs node(s) ont été identifié comme mort"""
        self._log.info("Some nodes ares dead : " , args)
        self._handleInitializationComplete(args)
        # TODO: nouvelle notification à identifier et gérer le fonctionnement

    def _handleNotification(self,  args):
        """Une erreur ou notification particulière est arrivée
        NotificationCode
            Code_MsgComplete = 0,					/**< Completed messages */
            Code_Timeout,						/**< Messages that timeout will send a Notification with this code. */
            Code_NoOperation,					/**< Report on NoOperation message sent completion  */
            Code_Awake,						/**< Report when a sleeping node wakes up */
            Code_Sleep,						/**< Report when a node goes to sleep */
            Code_Dead,						/**< Report when a node is presumed dead */
            Code_Alive						/**< Report when a node is revived */
        """
        node = self._getNode(args['homeId'], args['nodeId'])
        nCode = libopenzwave.PyNotificationCodes[args['notificationCode']]
        if not node:
            self._log.debug("Notification for node who doesn't exist : {0}".format(args))
        else :
            if nCode == 'MsgComplete':     #      Code_MsgComplete = 0,                                   /**< Completed messages */
                self._log.debug('MsgComplete notification code for Node {0}.'.format(node.refName))
                node.receivesCompletMsg(args)
            elif nCode == 'Timeout':         #      Code_Timeout,                                              /**< Messages that timeout will send a Notification with this code. */
                self._log.info('Timeout notification code for Node {0}.'.format(args['nodeId']))
            elif nCode == 'NoOperation':  #       Code_NoOperation,                                       /**< Report on NoOperation message sent completion  */
                self._log.info('Z-Wave Device Node {0} successful receipt testing message.'.format(node.refName))
                node.receivesNoOperation(args,  self.lastTest)
            elif nCode == 'Awake':            #      Code_Awake,                                                /**< Report when a sleeping node wakes up */
                node.setSleeping(False)
                self._log.info('Z-Wave sleeping device Node {0} wakes up.'.format(node.refName))
            elif nCode == 'Sleep':            #      Code_Sleep,                                                /**< Report when a node goes to sleep */
                node.setSleeping(True)
                node.receiveSleepState(args)
                self._log.info('Z-Wave Device Node {0} goes to sleep.'.format(node.refName))
            elif nCode == 'Dead':             #       Code_Dead                                               /**< Report when a node is presumed dead */
                node.markAsFailed()
                self._log.info('Z-Wave Device Node {0} marked as dead.'.format(node.refName))
            elif nCode == 'Alive':             #       Code_Alive						/**< Report when a node is revived */
                node.markAsOK()
                self._log.info('Z-Wave Device Node {0} marked as alive.'.format(node.refName))
            else :
                self._log.error('Error notification code unknown : ', args)

    def _handlePollingDisabled(self, args):
        """le polling d'une value commande classe a été désactivé."""
        self._log.info('Node {0} polling disabled.'.format(args['nodeId']))
        data = {'polled': False}
    #    data['id'] = str(args['valueId']['id'])
        self._plugin.publishMsg('ozwave.node.poll', {'NodeID': args['nodeId'], 'notifytype': 'polling', 'usermsg' : 'Polling disabled.', 'data': data})

    def _handlePollingEnabled(self, args):
        """le polling d'une value commande classe à été activé."""
        self._log.info('Node {0} polling enabled.'.format(args['nodeId']))
        data = {'polled': True}
     #   data['id'] = str(args['valueId']['id'])
        self._plugin.publishMsg('ozwave.node.poll', {'NodeID': args['nodeId'], 'notifytype': 'polling', 'usermsg' : 'Polling enabled.', 'data': data})

    def _handleNodeChanged(self, args):
        """Un node est ajouté ou a changé"""
        node = self._fetchNode(args['homeId'], args['nodeId'])
        node._lastUpdate = time.time()
        self._log.info(u"Node {0} is added or changed (homeId {1})".format(args['nodeId'], self.matchHomeID(args['homeId'])))

    def _handleNodeRemoved(self, args):
        """Un node est ajouté ou a changé"""
        node = self._getNode(args['homeId'], args['nodeId'])
        if node :
            ctrl = self.isNodeDeviceCtrl(node)
            if ctrl : self.removeDeviceCtrl(ctrl)
            self._plugin.publishMsg('ozwave.ctrl.report',{'NetworkID': node.networkID, 'NodeID': node.nodeId, 'type': 'node-removed',
                                                                          'usermsg' : 'Node {0} is exclude from zwave network'.format(node.refName)})
            self._nodes.pop(self.refNode(node.homeId, node.nodeId))
            self._log.info (u"Node {0} is removed (homeId {1})".format(args['nodeId'], self.matchHomeID(args['homeId'])))
        else :
            self._log.debug ("Node {0} unknown, isn't removed (homeId {1)".format(args['nodeId'], self.matchHomeID(args['homeId'])))

    def _handleValueAdded(self, args):
        """Un valueNode est ajouté au node depuis le réseaux zwave"""
        node = self._fetchNode(args['homeId'], args['nodeId'])
        node._lastUpdate = time.time()
        node.createValue(args['valueId'])

    def _handleValueRemoved(self, args):
        """Un valueNode est retiré au node depuis le réseaux zwave"""
        node = self._fetchNode(args['homeId'], args['nodeId'])
        node._lastUpdate = time.time()
        node.removeValue(args['valueId'])

    def _handleValueChanged(self, args):
        """"Un valuenode à changé sur le réseaux zwave"""
        valueId = args['valueId']
        node = self._fetchNode(args['homeId'], args['nodeId'])
        node._lastUpdate = time.time()
        valueNode = node.getValue(valueId['id'])
        try :
            if valueNode.updateData(valueId) and (valueNode.valueData['genre'] in ['System', 'Config']) :
                self.getCtrlOfNode(node).setSaveConfig(False)
        # formatage infos générales
        # ici l'idée est de passer tout les valeurs stats et trig en identifiants leur type par le label forcé en minuscule.
        # les labels sont listés le fichier json du plugin.
        # Le traitement pour chaque command_class s'effectue dans la valueNode correspondante.
            sensor_msg = valueNode.valueToSensorMsg()
            if sensor_msg : self._cb_send_sensor(sensor_msg['device'], sensor_msg['id'], sensor_msg['data_type'], sensor_msg['data']['current'])
        except :
            self._log.error(u"Error while reporting to ValueChanged : {0}".format(traceback.format_exc()))

    def _handleNodeEvent(self, args):
        """Un node à envoyé une Basic_Set command  au controleur.
        Cette notification est générée par certains capteur,  comme les decteurs de mouvement type PIR, pour indiquer qu'un événements a été détecter.
        Elle est aussi envoyée dans le cas d'une commande locale d'un device. """
  #     CmdsClassBasicType = ['COMMAND_CLASS_SWITCH_BINARY', 'COMMAND_CLASS_SENSOR_BINARY', 'COMMAND_CLASS_SENSOR_MULTILEVEL',
  #                                           'COMMAND_CLASS_SWITCH_MULTILEVEL',  'COMMAND_CLASS_SWITCH_ALL',  'COMMAND_CLASS_SWITCH_TOGGLE_BINARY',
  #                                           'COMMAND_CLASS_SWITCH_TOGGLE_MULTILEVEL', 'COMMAND_CLASS_SENSOR_MULTILEVEL', ]
        # recherche de la valueId qui a envoyée le NodeEvent
        node = self._fetchNode(args['homeId'], args['nodeId'])
        values = node.getValuesForCommandClass('COMMAND_CLASS_BASIC')
        print "*************** Node event handle *******"
        print node.productType
        if len(node.commandClasses) == 0 : node._updateCommandClasses()
        print node.commandClasses
        args2 = ""
        for classId in node.commandClasses :
            if PyManager.COMMAND_CLASS_DESC[classId] in CmdsClassBasicType :
                valuebasic = node.getValuesForCommandClass(PyManager.COMMAND_CLASS_DESC[classId] )
                args2 = dict(args)
                del args2['event']
                valuebasic[0].valueData['value'] = valuebasic[0].convertInType(args['event'])
                args2['valueId'] = valuebasic[0].valueData
                args2['notificationType'] = 'ValueChanged'
                break
        print "Valeur event :" ,  args['event']
        for value in values :
            print "-- Value :"
            print value
        if args2 :
            print "Event transmit à ValueChanged :"
            print args2
            self._handleValueChanged(args2)
            print"********** Node event handle fin du traitement ******"

    def _handleGroupChanged(self, args):
        """Report de changement d'association au seins d'un groupe"""
        node = self._fetchNode(args['homeId'], args['nodeId'])
        node.updateGroup(args['groupIdx'])

    def getCommandClassName(self, commandClassCode):
        """Retourn Le nom de la commande class en fonctionde son code."""
        return PyManager.COMMAND_CLASS_DESC[commandClassCode]

    def getCommandClassCode(self, commandClassName):
        """Retourn Le code de la command class en fonction de son nom."""
        for k, v in PyManager.COMMAND_CLASS_DESC.iteritems():
            if v == commandClassName:
                return k
        return None

    def _handleControllerCommand(self, args):
        """Handle controller command (action) Notification."""
        self._log.debug("Controller Command Notification : {0}".format(args))
        ctrl = self.getDeviceCtrl('homeID', args['homeId'])
        if ctrl :
            ctrl.handleNotificationCommand(args)
        else :
            self._log.warning ("Notification of ControllerCommand: OZWave controller not affectted for homeId {0)".format(self.matchHomeID(args['homeId'])))

    def handle_ControllerAction(self,  networkId,  action):
        """Transmet une action controleur a un controleur primaire."""
        ctrl = self.getCtrlOfNetwork(networkId)
        if self.isReady and ctrl :
            retval = ctrl.node.handle_Action(action)
        else :
            retval = action
            retval.update({'cmdstate': 'not running' , 'error': 'not controller', 'error_msg': 'Check your controller.'})
        return retval

    def  handle_ControllerSoftReset(self, networkId):
        """Transmmet le soft resset au controleur primaire."""
        retval = {'error': ''}
        if self.isReady :
            ctrl = self.getCtrlOfNetwork(networkId)
            if not ctrl.node.soft_reset() :
                retval['error'] = 'No reset for secondary controller'
        else : retval['error'] = 'Controller node not ready'
        return retval

    def  handle_ControllerHardReset(self, networkId):
        """
        Hard Reset a PC Z-Wave Controller.
        Resets a controller and erases its network configuration settings.  The
        controller becomes a primary controller ready to add devices to a new network.
        """
        retval = {'error': ''}
        ctrl = self.getCtrlOfNetwork(networkId)
        if ctrl is not None :
            if ctrl.ready :
                if ctrl.node.isPrimaryCtrl :
                    self._log.info(u'Start Hard Reset of ZWave controller on driver {0} with homeId {1}'.format(ctrl.driver, self.matchHomeID(ctrl.homeId)))
                    threading.Thread(None, self._hardResetcontroller, "th_hardResetcontroller", (ctrl.driver, ctrl.homeId,)).start()
                else:
                    retval['error'] = 'No possible Hard Reset on secondary controller {0}'.format(self.refName)
            else : retval['error'] = 'Controller for network {0} not ready, Hard Reset aborded.'.format(networkId)
        else : retval['error'] = 'No Controller Registered for network {0}'.format(networkId)
        return retval

    def _hardResetcontroller(self, driver, homeId):
        self._openingDriver = driver # openzwave reopen driver, so set plugin to wait for it.
        self._manager.resetController(homeId)
        self._log.info(u'Hard Reset of ZWave controller on driver :{0}, homeId :{1}, completed'.format(driver, self.matchHomeID(homeId)))
        self._plugin.publishMsg('ozwave.ctrl.state',{'Driver': driver, 'type': 'hard-reset',
                                                                          'usermsg' : 'Driver {0} is reseted with new homeId. All nodes are exclude'.format(driver)})

    def getOpenzwaveInfo(self):
        """ Retourne les infos de config d'openzwave (dict) """
        retval = {"status": "dead", "Options": {}}
        if self.options is not None:
            if self.options.areLocked :
                if self._manager is not None : retval["status"] = "alive"
                else : retval["status"] = "starting"
                for option in libopenzwave.PyOptionList :
                    retval["Options"][option] = libopenzwave.PyOptionList[option]
                    if option == 'NetworkKey' :
                        value = self.options.getOption(option)
                        retval["Options"][option]['value'] = "Secure Key Enable" if value != '' else "No Secure"
                        retval["Options"][option]['doc']  = "Network Key to use for Encrypting Secure Messages over the Network. Get/Set 16 Byte Key in options.xml file of Openzwave path."
                    else :
                        retval["Options"][option]['value']  = self.options.getOption(option)
                retval["error"] = ""
            else : retval["status"] = "stopped"
        retval["ConfigPath"] = self._configPath
        retval["UserPath"] = self._userPath
        retval["PYOZWLibVers"] = self.pyOZWLibVersion
        return retval

    def getManagerInfo(self):
        """ Retourne les infos du manager ozwave (dict) """
        retval = {"status": "dead"}
        if self.monitorNodes is None :
            retval["status"] = "starting"
        else : retval["status"] = "alive"
        retval["OZWPluginVers"] = self.pluginVers
        retval['init'] = ""
        retval["Controllers"] = []
        if self._devicesCtrl :
            for ctrl in self._devicesCtrl:
                ctrlInfos = self.getNetworkInfo(ctrl)
                retval["Controllers"].append(ctrlInfos)
            if not self.isReady : retval['init'] = "Zwave Controller(s) registered but at least one is not ready."
        else :
            if retval["status"] =="alive" : retval['init'] = "No controller registered, you must create domogik zwave primary controller."
            elif retval["status"] =="starting" : retval['init'] = "Manager starting and configure all services."
            else : retval['init'] = "Plugin fail, check the log."
        retval["error"] = ""
        return retval

    def getNetworkInfo(self, ctrl):
        """ Retourne les infos principales du réseau zwave (dict) """
        retval = {}
        if ctrl is not None :
            retval = ctrl.getStatus()
            retval["NetworkID"] = ctrl.networkID
            retval["HomeID"] = self.matchHomeID(ctrl.homeId)
            if ctrl.ready :
                if ctrl.node is not None :
                    retval["Model"] = "{0} -- {1}".format(ctrl.node.manufacturer, ctrl.node.product)
                    retval["NodeID"] = ctrl.node.nodeId
                    retval["Poll interval"] = ctrl.node.getPollInterval()
                else:
                    retval["Model"] = "Zwave controller not ready, be patient..."
                    retval["NodeID"] = 0
                    retval["Poll interval"] = 0
                retval["Protocol"] = self._manager.getControllerInterfaceType(ctrl.homeId)
                retval["Primary controller"] = ctrl.getControllerDescription()
                retval["Library"] = ctrl.libraryTypeName
                retval["Version"] = ctrl.libraryVersion
                retval["Node count"] = ctrl.getNodeCount()
                retval["Node sleeping"] = ctrl.getSleepingNodeCount()
                retval["Node fail"] = ctrl.getFailedNodeCount()
                retval["ListNodeId"] = ctrl.getNodesId()
            else:
                retval["Model"] = "Zwave network not ready, be patient..."
            retval["error"] = ""
            return retval
        else :
            retval["error"] = "Network ID <{0}> not registered, wait or check configuration and hardware.".format(networkId)
            retval["init"] = NodeStatusNW[0] # Uninitialized
            retval["status"] = "unknown"
            return retval

    def getZWRefFromDB(self, deviceID, id, type = 'cmd'):
        """ Return Zwave references from domogik DB
            @param : deviceID, Id of device in DB
            @param : id, id of sensor or command in DB
            @param : type, type of storage in DB, cmd (default) or sensor"""
        retval = {}
        for dmgDevice in self._plugin.devices :
            if dmgDevice['id'] == deviceID :
                if type == 'cmd' :
                    for cmd in dmgDevice['commands'] :
                        if dmgDevice['commands'][cmd]['id'] == id :
                            retval = {'networkid': dmgDevice['parameters']['networkid']['value'],
                                      'node': int(dmgDevice['parameters']['node']['value']),
                                      'instance': int(dmgDevice['parameters']['instance']['value']),
                                      'cmdParams': dmgDevice['commands'][cmd]['parameters']}
                            node = self._getNode(self.getHomeID(retval['networkid']), retval['node'])
                            self._log.debug(u"--- ZWRef Command Find : {0}, {1}".format(retval, node))
                            return retval
                else :
                    self._log.warning(u"getZWRefFromDB not handle type: {0}, deviceID: {1}, id: {2} ".format(type, deviceID, id))
        return retval

    def getDmgDevRefFromZW(self, device):
        """ Return device domogik address reference from ozwave object class.
            @param : device : one of class ZWaveController, ZWaveNode ou ZWaveValueNode """
        retval = {}
        if isinstance(device, ZWaveController):
            retval['networkid'] = self.getNetworkID(device.homeId)
        elif isinstance(device, ZWaveNode):
            retval['networkid'] = self.getNetworkID(device.homeId)
            retval['node'] = device.nodeId
        elif isinstance(device, ZWaveValueNode):
            retval['networkid'] = self.getNetworkID(device.homeId)
            retval['node'] = device.nodeId
            retval['instance'] = device.instance
        else: retval = None
        return retval

    def _getDmgDevice(self, device):
        """Return the domogik device if exist else None.
            return the device for network (list)
            return list of devices for node
            return the device for value (instance) (list)"""
        logLine = u"--- Search dmg device for : {0}".format(device)
        dmgDevices = []
        for dmgDevice in self._plugin.devices :
#            logLine += u"\n        - in dmg device : {0}".format(dmgDevice)
            if 'instance' in dmgDevice['parameters']: # Value sensor or command level
                if isinstance(device, ZWaveValueNode):
                    try :
                        if int(dmgDevice['parameters']['instance']['value']) == device.instance and \
                           int(dmgDevice['parameters']['node']['value']) == device.nodeId and \
                           dmgDevice['parameters']['networkid']['value'] == device.networkID :
                            dmgDevices.append(dmgDevice)
#                            logLine += u"\n            --- add device from value : {0}".format(dmgDevice)
#                            logLine += u"\n            --- {0}".format(dmgDevices)
                    except :
                        self._log.error(u"Domogik device ({0}) bad format address : {1}".format(dmgDevice['name'], dmgDevice['parameters']))
            elif 'node' in dmgDevice['parameters']: # Node level
                if isinstance(device, ZWaveNode):
                    try :
                        if int(dmgDevice['parameters']['node']['value']) == device.nodeId and \
                           dmgDevice['parameters']['networkid']['value'] == device.networkID :
                            dmgDevices.append(dmgDevice)
#                            logLine += u"\n            --- add device from node: {0}".format(dmgDevice)
                    except :
                        self._log.error(u"Domogik device ({0}) bad format address : {1}".format(dmgDevice['name'], dmgDevice['parameters']))
            elif 'networkid' in dmgDevice['parameters']: # primary controller level
                if isinstance(device, ZWaveController):
                    if dmgDevice['parameters']['networkid']['value'] == device.networkID :
                        dmgDevices.append(dmgDevice)
#                        logLine += u"\n            --- add device from ctrl: {0}".format(dmgDevice)
#            else :
#                logLine += u"\n    --- no key find"
#        if not dmgDevices : logLine += u"\n    --- Dmg device NOT find"
#        self._log.debug(logLine)
        if dmgDevices :
            self._log.debug(u"--- devices :{0}".format(dmgDevices))
            return dmgDevices
        return []

    def sendCmdToZW(self, device, command, cmdValue):
        """Message come from MQ. Send command to wave network
            @param : device = dict{'homeId', 'nodeId', 'instance', 'cmdParams'}
            @param : command = the command value define in json
            @param : cmdValue = extra key with value, mostly the value of DT_Type
        """
        if device != None :
            node = self._getNode(self.getHomeID(device['networkid']), device['node'])
            if node : node.sendCmdBasic(device, command, cmdValue)

    def getNodeInfos(self, homeId, nodeId):
        """ Retourne les informations d'un device, format dict{} """
        if self.isReady :
            node = self._getNode(homeId, nodeId)
            if node : return node.getInfos()
            else : return {"error" : "Unknown Node : {0}.{1}".format(homeId, nodeId)}
        else : return {"error" : "Zwave network not ready, can't find node %{0}.{1}".format(homeId, nodeId)}

    def refreshNodeDynamic(self, homeId, nodeId):
        """ Force un rafraichissement des informations du node depuis le reseaux zwave"""
        if self.isReady :
            node = self._getNode(homeId,  nodeId)
            if node : return node.requestNodeDynamic()
            else : return {"error" : "Unknown Node : {0}".format(node.refName)}
        else : return {"error" : "Zwave network not ready, can't find node {0}".format(node.refName)}

    def refreshNodeInfo(self, homeId, nodeId):
        """ Force un rafraichissement des informations du node depuis le reseaux zwave"""
        if self.isReady :
            node = self._getNode(homeId,  nodeId)
            if node : return node.requestNodeInfo()
            else : return {"error" : "Unknown Node : %d" % nodeId}
        else : return {"error" : "Zwave network not ready, can't find node {0}".format(node.refName)}

    def refreshNodeState(self, homeId, nodeId):
        """ Force un rafraichissement des informations primaires du node depuis le reseaux zwave"""
        if self.isReady :
            node = self._getNode(homeId, nodeId)
            if node : return node.requestNodeState()
            else : return {"error" : "Unknown Node : {0}".format(node.refName)}
        else : return {"error" : "Zwave network not ready, can't find node {0}".format(node.refName)}

    def getNodeValuesInfos(self, homeId, nodeId):
        """ Retourne les informations de values d'un device, format dict{} """
        if self.isReady :
            node = self._getNode(homeId, nodeId)
            if node : return node.getValuesInfos()
            else : return {"error" : "Unknown Node : %d" % nodeId}
        else : return {"error" : "Zwave network not ready, can't find node {0}".format(node.refName)}

    def getValueInfos(self, homeId, nodeId,  valueId):
        """ Retourne les informations d'une value d'un device, format dict{} """
        retval = {}
        if self.isReady :
            node = self._getNode(homeId, nodeId)
            if node :
                value = node.getValue(valueId)
                if value :
                    retval = value.getInfos()
                    retval['error'] = ""
                    return retval
                else : return {"error" : "Unknown value : %d" % valueId}
            else : return {"error" : "Unknown Node : %d" % nodeId}
        else : return {"error" : "Zwave network not ready, can't find value %d" % valueId}

    def getValueTypes(self):
        """return list of value type de and doc associate (dict)"""
        retval = {}
        for elem in  libopenzwave.PyValueTypes :
            retval[elem] = elem.doc
        return retval

    def getListStatDriver(self):
        """ Return list of data driver statistic and doc associate (dict)"""
        return libopenzwave.PyStatDriver

    def getListStatNode(self):
        """ Return list of data Node statistic and doc associate (dict)"""
        return { "sentCnt" : "Number of messages sent from this node.",
                 "sentFailed" :  "Number of sent messages failed",
                 "retries" :  "Number of message retries",
                 "receivedCnt" :  "Number of messages received from this node.",
                 "receivedDups" :  "Number of duplicated messages received.",
                 "receivedUnsolicited" :  "Number of messages received unsolicited.",
                 "sentTS" :  "Last message sent time.",
                 "receivedTS" :  "Last message received time",
                 "lastRequestRTT " :  "Last message request RTT",
                 "averageRequestRTT" :  "Average Request Round Trip Time (ms).",
                 "lastResponseRTT" :  "Last message response RTT",
                 "averageResponseRTT" :  "Average Reponse round trip time.",
                 "quality" :  "Node quality measure",
                 "lastReceivedMessage" :  "Last received raw data message",
                 "commandClassId" :  "Individual Stats for: ",
                 "sentCntCC" :  "Number of messages sent from this CommandClass.",
                 "receivedCntCC" :  "Number of messages received from this CommandClass."
                }

    def testNetwork(self, networkId, count = 1, timeOut = 10000,  allReport = False):
        """Envois une serie de messages à tous les nodes pour tester la réactivité du réseaux."""
        ctrl = self.getCtrlOfNetwork(networkId)
        if ctrl is None : return {"error" : "Zwave network not ready, can't find controller"}
        if ctrl.node is None : return {"error" : "Zwave network not ready, can't find node controller"}
        if ctrl.ready :
            retval = {'error' :'', 'nodes': []}
            for node in self._nodes.itervalues() :
                if (node.homeId == ctrl.homeId) and (not node.isSleeping) and (self.isNodeDeviceCtrl(node)) is None :
                    error = node.trigTest(count, timeOut,  allReport,  False)
                    if error['error'] != '' :
                        retval['error'] = retval['error'] +'/n' + error['error']
                    else : retval['nodes'].append(node.refName)
            self.lastTest = time.time()
            self._manager.testNetwork(ctrl.homeId, count)
            if retval['error'] != '': retval['error'] = 'Some node(s) have error :/n' + retval['error']
            return retval
        else : return {"error" : "Zwave network not ready, can't find controller.", 'nodes': []}

    def testNetworkNode(self, homeId, nodeId, count = 1, timeOut = 10000, allReport = False):
        """Envois une serie de messages à un node pour tester sa réactivité sur le réseaux."""
        ctrl = self.getCtrlOfNetwork(homeId)
        if ctrl is None : return {"error" : "Zwave network not ready, can't find controller"}
        if ctrl.ready :
            node = self._getNode(homeId,  nodeId)
            if self.isNodeDeviceCtrl(node) is None :
                if node : retval = node.testNetworkNode(count, timeOut, allReport)
                else : retval['error'] = "Zwave node {0} unknown.".format(node.refName)
            else : retval['error'] = "Can't test primary controller, node {0}.".format(node.refName)
            return retval
        else : return {"error" : "Zwave network not ready, can't find node {0}".format(node.refName)}

    def healNetwork(self, networkId, upNodeRoute):
        """Tente de 'réparé' des nodes pouvant avoir un problème. Passe tous les nodes un par un"""
        ctrl = self.getCtrlOfNetwork(networkId)
        if ctrl is None : return {"error" : "Zwave network not ready, can't find controller."}
        if ctrl.ready :
            self._manager.healNetwork(ctrl.homeId, upNodeRoute)
            if upNodeRoute :
                for node in self._nodes.itervalues(): node._updateNeighbors()
            return {"error": ""}
        else : return {"error": "Zwave network not ready, wait ready to heal network."}

    def healNetworkNode(self, homeId, nodeId, upNodeRoute):
        """Tente de 'réparé' un node particulier pouvant avoir un problème."""
        ctrl = self.getCtrlOfNetwork(homeId)
        if ctrl is None : return {"error" : "Zwave network not ready, can't find controller"}
        if ctrl.ready :
            node = self._getNode(homeId,  nodeId)
            if node :
                self._manager.healNetworkNode(ctrl.homeId, nodeId, upNodeRoute)
                if upNodeRoute : node._updateNeighbors()

    def getGeneralStatistics(self, networkId):
        """Retourne les statistic générales du réseaux"""
        retval={}
        ctrl = self.getCtrlOfNetwork(networkId)
        if ctrl is None : return {"error" : "Zwave network not ready, can't find controller"}
        if ctrl.node is None : return {"error" : "Zwave network not ready, can't find node controller"}
        if ctrl.ready :
            retval = ctrl.node.stats()
            retval['error'] = "" if retval else "No response of Zwave controller."
            retval['msqueue'] = ctrl.getCountMsgQueue()
            retval['elapsedtime'] = str(timedelta(0,time.time() - ctrl.timeStarted))
            return retval
        else : return {"error" : "Zwave network not ready, controller not ready"}

    def getNodeStatistics(self, homeId,  nodeId):
        """Retourne les statistic d'un node"""
        retval = {}
        ctrl = self.getCtrlOfNetwork(homeId)
        if ctrl.ready :
            node = self._getNode(ctrl.homeId,  nodeId)
            if node :
                retval = node.getStatistics()
                if retval :
                    retval['error'] = ""
                    for item in retval['ccData'] :
                        item['commandClassId']  = self.getCommandClassName(item['commandClassId'] ) + ' (' + hex(item['commandClassId'] ) +')'
                else : retval = {'error' : "Zwave node {0} not response.".format(node.refName)}
            else : retval['error'] = "Zwave node %d unknown" %node.refName
            return retval
        else : return {"error" : "Zwave network not ready, can't find node {0}".format(node.refName)}

    def setUINodeNameLoc(self, homeId, nodeId,  newname, newloc):
        """Change le nom et/ou le localisation du node dans OZW et dans le decive si celui-ci le supporte """
        ctrl = self.getCtrlOfNetwork(homeId)
        if ctrl.ready :
            node = self._getNode(ctrl.homeId,  nodeId)
            if newname != 'Undefined' and node.name != newname :
                try :
                    node.setName(newname)
                    ctrl.setSaveConfig(False)
                except Exception as e:
                    self._log.error('node.setName() :' + e.message)
                    return {"error" : "Node %d, can't update name, error : %s" %(nodeId, e.message) }
            if newloc != 'Undefined' and node.location != newloc :
                try :
                    node.setLocation(newloc)
                    ctrl.setSaveConfig(False)
                except Exception as e:
                    self._log.error('node.setLocation() :' + e.message)
                    return {"error" : "Node %d, can't update location, error : %s" %(nodeId, e.message) }
            return node.getInfos()
        else : return {"error" : "Zwave network not ready, can't find node %d" %nodeId}

    def setValue(self, homeId,  nodeId,  valueId,  newValue):
        """Envoie la valeur a l'objet value"""
        retval = {}
        ctrl = self.getCtrlOfNetwork(homeId)
        if ctrl.ready :
            node = self._getNode(ctrl.homeId,  nodeId)
            if node :
                value = node.getValue(valueId)
                if value :
                    retval = value.setValue(newValue)
                    return retval
                else : return {"value": newValue, "error" : "Unknown value : %d" %valId}
            else : return {"error" : "Unknown Node : %d" % nodeId}
        else : return {"value": newValue, "error" : "Zwave network not ready, can't find value %d" %valId}

    def setMembersGrps(self,  homeId, nodeId, newGroups):
        """Envoie les changement des associations de nodes dans les groups d'association."""
        retval = {}
        ctrl = self.getCtrlOfNetwork(homeId)
        if ctrl.ready :
            node = self._getNode(homeId,  nodeId)
            if node :
                grp =node.setMembersGrps(newGroups)
                if grp :
                    retval['groups'] = grp
                    retval['error'] = ""
                    return retval
                else : return {"error" : "Manager not send association changement on node %d." %nodeId}
                return retval
            else : return {"error" : "Unknown Node : %d" % nodeId}
        else : return {"error" : "Zwave network not ready, can't find node %d" % nodeId}

    def processRequest(self, request, data):
        """Callback come from MQ (request with reply)"""
        report = {}
        try :
            reqRef = request.split('.')
            if reqRef[0] not in ['openzwave','manager'] :
                if not 'homeId' in data : data['homeId'] = self._devicesCtrl[0].homeId
                if not 'networkId' in data : data['networkId'] = self.getNetworkID(data['homeId'])
                else : data['homeId'] = self.getCtrlOfNetwork(data['networkId']).homeId
                if 'nodeId' in data : data['nodeId'] =  int(data['nodeId'])
                ctrl = self.getCtrlOfNetwork(data['networkId'])
            else :
                ctrl = None
        except Exception as e:
            self._log.warning(e.message)
            return {'error':'Bad request ({0}) parameters : {1}'.format(request, data)}
        if reqRef[0] == 'ctrl':
            report = self._handleControllerRequest(request, data)
        elif reqRef[0] == 'node':
            report = self._handleNodeRequest(request, data)
        elif reqRef[0] == 'value':
            report = self._handleValueRequest(request, data)
        # Plugin and openzwave request don't need controller.
        elif request == 'manager.get' :
            report = self.getManagerInfo()
        elif request == 'manager.refreshdeviceslist':
            self.threadingRefreshDevices()
            report = {'error':''}
        elif request == 'openzwave.get' :
            report = self.getOpenzwaveInfo()
        elif request == 'openzwave.getallproducts':
            report = self.getAllProducts()
        elif request == 'openzwave.getproduct':
            report = self.getProduct(data['productName'])
        elif request == 'openzwave.getmemoryusage':
            report = self.getMemoryUsage()
        elif request == 'openzwave.getlog':
            report = self.getLoglines(data)
        elif request == 'openzwave.getlogozw':
            report = self.getLogOZWlines(data)

        elif request == 'SetPollInterval':
            ctrl.node.setPollInterval(data['interval'],  False)
            report['interval'] = ctrl.node.getPollInterval()
            if  report['interval'] == data['interval']:
                report = {'error':''}
            else :
                report = {'error':'Setting interval error : keep value %d ms.' %report['interval']}

        # Openzwave constants
        elif request == 'openzwave.getvaluetypes':
            report = self.getValueTypes()
        elif request == 'openzwave.getstatdriverinfos':
            report = self.getListStatDriver()
        elif request == 'openzwave.getstatnodeinfos':
            report = self.getListStatNode()

        else :
            report['error'] ='Unknown request <{0}>, data : {1}'.format(request,  data)
        return report

    def _handleControllerRequest(self, request, data):
        """Handle all zwave controller request coming from MQ"""
        ctrl = self.getCtrlOfNetwork(data['networkId'])
        report = {}
        if ctrl is not None :
            if request == 'ctrl.get' :
                report = self.getNetworkInfo(self.getCtrlOfNetwork(data['networkId']))
            elif request == 'ctrl.nodes' :
                report['nodes'] = []
                for nodeId in ctrl.getNodesId():
                    report['nodes'].append(self.getNodeInfos(data['homeId'], nodeId))
            elif request == 'ctrl.action' :
                report = self.handle_ControllerAction(data['networkId'],  json.loads(data['action']))
            elif request == 'ctrl.saveconf':
                report = ctrl.saveNetworkConfig()
            elif request == 'ctrl.start':
                if ctrl.status != 'open' :
                    self.openDeviceCtrl(ctrl)
                    report = {'error':'',  'running': True}
                else : report = {'error':'Driver already running. For restart stop it before',  'running': True}
            elif request == 'ctrl.stop':
                if ctrl.status =='open' :
                    self.removeDeviceCtrl(ctrl)
                    report = {'error':'',  'running': False}
                else : report = {'error':'No Driver knows.',  'running': False}
            elif request == 'ctrl.healnetwork' :
                report = self.healNetwork(data['networkId'], data['forceroute'])
            elif request == 'ctrl.softreset' :
                report = self.handle_ControllerSoftReset(data['networkId'])
            elif request == 'ctrl.hardreset' :
                report = self.handle_ControllerHardReset(data['networkId'])
            elif request == 'ctrl.getlistcmdsctrl':
                report = ctrl.getListCmdsCtrl()
            elif request == 'ctrl.getnetworkstats':
                report = self.getGeneralStatistics(data['networkId'])
            elif request == 'ctrl.testnetwork':
                report = self.testNetwork(data["networkId"], int(data['count']),  10000, True)
            else :
                report['error'] ='Unknown request <{0}>, data : {1}'.format(request,  data)
            report.update({'NetworkID': data['networkId'], 'Driver': ctrl.driver})
        else :
            report["error"] = "Network ID <{0}> not registered, wait or check configuration and hardware.".format(data['networkId'])
            report["init"] = NodeStatusNW[0] # Uninitialized
            report["state"] = "unknown"
            report.update({'NetworkID': data['networkId'], 'Driver': 'unknown'})
        return report

    def _handleNodeRequest(self, request, data):
        """Handle all zwave node request coming from MQ"""
#        ctrl = self.getCtrlOfNetwork(data['networkId'])
        report = {}
        if request == 'node.infos' :
            if self._IsNodeId(data['nodeId']):
                report = self.getNodeInfos(data['homeId'], data['nodeId'])
            else : report = {'error':  'Invalide nodeId format.'}
        elif request == 'node.set':
            if data['key'] == "name" :
                report = self.setUINodeNameLoc(data['homeId'], data['nodeId'], data['value'], "Undefined")
            elif data['key'] == "location" :
                report = self.setUINodeNameLoc(data['homeId'], data['nodeId'], "Undefined", data['value'])
            elif data['key'] == 'groups':
                if self._IsNodeId(data['nodeId']):
                    data['ngrps'] = json.loads(data['ngrps'])  # MQ Array in json string format.
                    report = self.setMembersGrps(data['homeId'], data['nodeId'], data['ngrps'])
                else : report = {'error':  'Invalide nodeId format.'}
            else :
                report['error'] ='Request {0} unknown key to set, data : {1}'.format(request,  data)
        elif request == 'node.get':
            if data['key'] == 'values':
                if self._IsNodeId(data['nodeId']):
                    report =self.getNodeValuesInfos(data['networkId'], data['nodeId'])
                else : report = {'error':  'Invalide nodeId format.'}
        elif request == 'node.action' :
            if data['action'] == 'StartMonitorNode':
                if self._IsNodeId(data['nodeId']):
                    report = self.monitorNodes.startMonitorNode(data["homeId"], data['nodeId'])
                else : report = {'error':  'Invalide nodeId format.'}
            elif data['action'] == 'StopMonitorNode':
                if self._IsNodeId(data['nodeId']):
                    report = self.monitorNodes.stopMonitorNode(data["homeId"], data['nodeId'])
                else : report = {'error':  'Invalide nodeId format.'}
            elif data['action'] == 'RefreshNodeDynamic' :
                if self._IsNodeId(data['nodeId']):
                    report = self.refreshNodeDynamic(data['homeId'], data['nodeId'])
                else : report = {'error':  'Invalide nodeId format.'}
            elif data['action'] == 'RefreshNodeInfo' :
                if self._IsNodeId(data['nodeId']):
                    report = self.refreshNodeInfo(data['homeId'], data['nodeId'])
                else : report = {'error':  'Invalide nodeId format.'}
            elif data['action'] == 'RefreshNodeState' :
                if self._IsNodeId(data['nodeId']):
                    report = self.refreshNodeState(data['homeId'], data['nodeId'])
                else : report = {'error':  'Invalide nodeId format.'}
            elif data['action'] == 'HealNode' :
                if self._IsNodeId(data['nodeId']):
                    data['forceroute'] = True #Not in optionfor the momment
                    self.healNetworkNode(data['networkId'],  data['nodeId'],  data['forceroute'])
                    report = {'usermsg':'Command heal node sended, please wait for result...'}
                else : report = {'error':  'Invalide nodeId format.'}
            elif data['action'] == 'batterycheck' :
                node = self._getNode(data['homeId'], data['nodeId'])
                if node :
                    report['state'] = node.setBatteryCheck(True if data['state'] in [True, 'True', 'true'] else False)
                    report['error'] = ''
                else : report = {'error':  "Node {0}.{1} doesn't exist.".format(data['homeId'], data['nodeId'])}
            elif data['action'] == 'UpdateConfigParams' :
                node = self._getNode(data['homeId'], data['nodeId'])
                if node :
                    report = node.updateConfig()
                else : report = {'error':  "Node {0}.{1} doesn't exist.".format(data['homeId'], data['nodeId'])}
            elif data['action'] == 'RefrechDetectDev' :
                node = self._getNode(data['homeId'], data['nodeId'])
                if node :
                    threading.Thread(None, node._checkDmgDeviceLink, "th_refreshDevices", (), {"force": True}).start()
                    report['error'] = ''
                    report['usermsg'] = u"Domogik detection devices for node {0} started ...".format(node.refName)
                else : report = {'error':  "Node {0}.{1} doesn't exist.".format(data['homeId'], data['nodeId'])}
            else :
                report['error'] ='Request {0} unknown action, data : {1}'.format(request, data)
            report['action'] = data['action']
        elif request == 'node.getnodestats':
            if self._IsNodeId(data['nodeId']):
                report = self.getNodeStatistics(data['homeId'], data['nodeId'])
            else : report = {'error':  'Invalide nodeId format.'}
        elif request == 'node.testnetworknode':
            if self._IsNodeId(data['nodeId']):
                report = self.testNetworkNode(data["homeId"], data['nodeId'], int(data['count']), 10000, True)
            else : report = {'error': u'Invalide nodeId format.'}
        else :
            report['error'] = u'Unknown request <{0}>, data : {1}'.format(request, data)
        report.update({'NetworkID': data['networkId'], 'NodeID': data['nodeId']})
        return report

    def _handleValueRequest(self, request, data):
        """Handle all zwave node request coming from MQ"""
        ctrl = self.getCtrlOfNetwork(data['networkId'])
        report = {}
        if request == 'value.infos':
            if self._IsNodeId(data['nodeId']):
                valId = long(data['valueId']) # Pour javascript type string
                report =self.getValueInfos(data['nodeId'], valId)
            else : report = {'error': u'Invalide nodeId format.'}
        elif request == 'value.set' :
            if self._IsNodeId(data['nodeId']):
                valId = long(data['valueId']) # Pour javascript type string
                report = self.setValue(data['homeId'], data['nodeId'], valId, data['newValue'])
            else : report = {'error': u'Invalide nodeId format.'}
        elif request == 'value.reqRefresh' :
            node = self._getNode(data['homeId'], data['nodeId'])
            if node :
                valId = long(data['valueId']) # Pour javascript type string
                value = node.getValue(valId)
                report = value.RefreshOZWValue()
            else : report = {'error':  u"Node {0}.{1} doesn't exist.".format(data['homeId'], data['nodeId'])}
        elif request == 'value.poll':
            valId = long(data['valueId']) # Pour javascript type string
            data['intensity'] = int(data['intensity'])
            node = self._getNode(data['homeId'], data['nodeId'])
            if node :
                if data['action'] == 'EnablePoll' :
                    report = ctrl.node.enablePoll(data['nodeId'],  valId,  data['intensity'])
                elif data['action'] == 'DisablePoll':
                    report = ctrl.node.disablePoll(data['nodeId'],  valId)
                    value.setPollIntensity(data['intensity'])
                else :
                    report['error'] = u'Request {0} unknown action, data : {1}'.format(request,  data)
            else : report = {'error':  u"Node {0}.{1} doesn't exist.".format(data['homeId'], data['nodeId'])}
            report.update({'action': data['action'], 'intensity': data['intensity']})
        else :
            report['error'] = u'Unknown request <{0}>, data : {1}'.format(request,  data)
        report.update({'NetworkID': data['networkId'], 'NodeID': data['nodeId'], 'ValueID': data['valueId']})
        return report

    def reportCtrlMsg(self, networkId, ctrlmsg):
        """A change state message is received, it's report on MQ for l'UI
        """
        report  = {}
        ctrl = self.getCtrlOfNetwork(networkId)
        if ctrl is None : return
        if ctrl.ctrlActProgress :
            report = ctrl.ctrlActProgress
        else :
            report['action'] = 'undefine'
            report['id'] = 0
            report['cmd'] = 'undefine'
            report['cptmsg'] = 0
            report['cmdSource'] = 'undefine'
            report['arg'] ={}
        report['state'] = ctrlmsg['state']
        report['error'] = ctrlmsg['error']
        report['message'] = ctrlmsg['message']
        if ctrlmsg['error_msg'] != 'None.' : report['err_msg'] = ctrlmsg['error_msg']
        else : report['err_msg'] = 'no'
        report['update'] = ctrlmsg['update']
        if ctrlmsg['state'] == libopenzwave.PyControllerState[8] : # Failed
            node = self._getNode(networkId, ctrlmsg['nodeid'])
            if node : node.markAsFailed();
        if ctrlmsg['state'] == libopenzwave.PyControllerState[9] : # NodeOK :
            node = self._getNode(networkId, ctrlmsg['nodeid'])
            if node : node.markAsOK()
        if ctrlmsg['state'] not in [libopenzwave.PyControllerState[1], libopenzwave.PyControllerState[4],
                                              libopenzwave.PyControllerState[5], libopenzwave.PyControllerState[6]] :
            report['cmdstate'] = 'stop'
            ctrl.ctrlActProgress= None
        else :
            report['cmdstate'] = 'waiting'
        msg = {'notifytype': 'ctrlstate'}
        msg['data'] = report
        self._plugin.publishMsg('ozwave.ctrl.state', msg)

class PrimaryController():
    """Objet de liaison entre un device domogik un controleur primaire zwave.
        La class mémorise et compile des informations sur le controleur primaire et son réseaux de nodes,
        mais ne fait aucune action dans la lib openzwave. Celle-ci sont faite dans le manager OZWavemanager
        ou dans le node controleur ZWaveController.
    """

    def __init__(self, ozwmanager, driver,  networkID,  homeId = None):
        """Initialisation """
        self._ozwmanager = ozwmanager
        self.driver = driver
        self.networkID = networkID
        self.homeId = homeId
        self.status = 'close'
        self.ready = False
        self.initFully = False
        self._saved = False
        self.node = None
        self.nodeId = 0
        self.libraryVersion = "Unknown"
        self.libraryTypeName = "Unknown"
        self.timeStarted = 0
        self.controllercaps = None

    isSaved = property(lambda self: self._saved)
    ctrlActProgress = property(lambda self: None if self.node is None else self.node.getLastState())

    def __str__(self):
        return u"driver = {0}, networkID = {1}, homeId = {2}, status = {3}, ready = {4}".format(self.driver, self.networkID , self.homeId, self.status, self.ready)

    def setClosed(self):
        self.status = 'close'
        self.ready = False
        self.initFully = False
        self._saved = False
        self.timeStarted = 0

    def saveNetworkConfig(self):
        """Enregistre le configuration au format xml"""
        retval = {"NetworkID": self.networkID}
        if self.node is not None :
            self.node._manager.writeConfig(self.homeId)
            self._saved = True
            retval["result"] = "success"
            retval["error"] = ""
            retval["saved"] = True
            retval["msg"] = "Network {0} config saved on file zwcfg_{1}.xml in user path.".format(self.networkID, self._ozwmanager.matchHomeID(self.homeId))
            self.node.log.info("Openzwave config file saved : {0}zwcfg_{1}.xml".format(self._ozwmanager._userPath, self._ozwmanager.matchHomeID(self.homeId)))
        else :
            retval["result"] = "error"
            retval["error"] = "Controller not fully init. can't save configuration."
            retval["msg"] = "file zwcfg_{1}.xml Not saved.".format(self._ozwmanager.matchHomeID(self.homeId))
            retval["saved"] = False
            self.node.log.warning("Controller {0} not fully init. can't save configuration.".format(self.networkID))
        return retval

    def setSaveConfig(self,  saved = False):
        self._saved = saved
        self._ozwmanager._plugin.publishMsg('ozwave.ctrl.saveconfchange', {"NetworkID": self.networkID, "saved": saved})

    def getCountMsgQueue(self):
        """Return number of message in openzwave outgoing send queue."""
        if self.node is not None :
            return self.node._manager.getSendQueueCount(self.homeId)
        else : return 0

    def getListCmdsCtrl(self):
        """Retourne le liste des commandes possibles du controleur ainsi que la doc associée."""
        retval = {"NetworkID": self.networkID}
        if self.node is None : return {"error" : "Zwave network not ready, node controller unknown, can't get command list."}
        else :
            retval['ctrlactions'] = self.node.cmdsAvailables()
            retval['error'] = ""
            return retval

    def getControllerDescription(self):
        """Renvoi la description du controleur (fabriquant et produit)"""
        if self.node and self.node._product:
            return self.node._product.name
        return 'Unknown Controller'

    def getLibraryDescription(self):
        """Renvoi le type de librairie ainsi que la version du controleur du réseaux zwave HomeID"""
        if self.libraryTypeName and self.libraryVersion:
            return '{0} Library Version {1}'.format(self._libraryTypeName, self._libraryVersion)
        else:
            return 'Unknown'

    def getStatus(self):
        """Renvoi l'état du controleur."""
        retval = {}
        retval["init"] = NodeStatusNW[0] # Uninitialized
        retval["status"] = 'unknown'
        retval["saved"] = self._saved
        if self.status == 'open' :
            retval["status"] = 'alive'
            if self.ready :
                if self.initFully :
                    retval["init"] = NodeStatusNW[2] # Completed
                else :
                    retval["init"] = NodeStatusNW[3] # In progress - Devices initializing
                    retval["status"] = 'starting'
            if self.ctrlActProgress and self.ctrlActProgress.has_key('state') and self.ctrlActProgress['state'] == libopenzwave.PyControllerState[4] :
                retval['status'] ='locked' #Waiting
        elif self.status == 'close' : retval["status"] = 'stopped'
        elif self.status == 'fail' :
            retval["status"] = 'dead'
            retval["init"] = 'Out of operation'
        return retval

    def getNodes(self):
        """ Renvoi la liste des nodes du reseaux."""
        retval = []
        if self.node is not None :
            for node in self._ozwmanager._nodes.itervalues():
                if node.homeId == self.homeId:
                    retval.append(node)
        return retval

    def getNodesId(self):
        """ Renvoi la liste des nodes du reseaux."""
        retval = []
        if self.node is not None :
            for node in self._ozwmanager._nodes.itervalues():
                if node.homeId == self.homeId:
                    retval.append(node.nodeId)
        return retval

    def getNodeCount(self):
        """Renvoi le nombre de node du reseaux."""
        retval = 0
        if self.node is not None :
            for node in self._ozwmanager._nodes.itervalues():
                if node.homeId == self.homeId:
                    retval += 1
        return retval

    def getSleepingNodeCount(self):
        """Renvoi le nombre de node du reseaux en veille."""
        retval = 0
        if self.node is not None :
            for node in self._ozwmanager._nodes.itervalues():
                if node.homeId == self.homeId and node.isSleeping:
                    retval += 1
        return retval

    def getFailedNodeCount(self):
        """Renvoi le nombre de node du reseaux considere HS."""
        retval = 0
        if self.node is not None :
            for node in self._ozwmanager._nodes.itervalues():
                if node.homeId == self.homeId and node.isFailed:
                    retval += 1
        return retval

    def getNodeCountDescription(self):
        """Renvoi le nombre de node total et/ou le nombre en veille du reseaux (return str)"""
        retval = '{0} Nodes'.format(self.getNodeCount)
        sleepCount = self.getSleepingNodeCount()
        failCount = self.getSleepingNodeCount()
        if sleepCount:
            retval = '{0} ({1} sleeping)'.format(retval, sleepCount)
        if failCount :  retval += '({0} dead)'.format(failCount)
        return retval

    def handleNotificationCommand(self, args):
        """Handle notification ControllerCommand from openzwave."""
        if self.node is not None :
            self.node.handleNotificationCommand(args)
        else :
            self._ozwmanager._plugin.publishMsg('ozwave.ctrl.command', {'NetworkID': self.networkID,
                'state': args['controllerState'],
                'usermsg' : args['controllerStateDoc'],
                'error' : '' if args['controllerError'] == 'None' else args['controllerErrorDoc'],
                'command' : 'Internal',
                'nodeId': args['nodeId']
               })
