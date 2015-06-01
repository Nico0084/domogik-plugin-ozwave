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
Version for domogik >= 0.4

Implements
========

- Zwave

@author: Nico <nico84dev@gmail.com>
@copyright: (C) 2007-2015 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

from domogik.common.configloader import Loader

import threading
import libopenzwave
from libopenzwave import PyManager
from ozwvalue import ZWaveValueNode
from ozwnode import ZWaveNode
from ozwctrl import ZWaveController
from ozwxmlfiles import *
from ozwmonitornodes import ManageMonitorNodes
#from wsuiserver import BroadcastServer
from ozwmqworker import OZWMQRep
from ozwdefs import *
from datetime import timedelta
import pwd
import sys
import resource
import traceback
import tailer
import re
import os
import time

class OZwaveManagerException(OZwaveException):
    """"Zwave Manager exception  class"""
            
    def __init__(self, value):
        OZwaveException.__init__(self, value)
        self.msg = "OZwave Manager exception:"
                                                    

class OZWavemanager():
    """
    ZWave class manager
    """

    def __init__(self, xplPlugin,  cb_send_xPL, cb_sendxPL_trig, stop , log,  configPath, userPath, ozwlog = False):
        """ Ouverture du manager py-openzwave
            @ param config : configuration du plugin pour accès aux valeurs paramètrées"
            @ param cb_send_xpl : callback pour envoi msg xpl
            @ param cb_send_trig : callback pour trig xpl
            @ param stop : flag d'arrêt du plugin         
            @ param log : log instance domogik
            @ param configPath : chemin d'accès au répertoire de configuration pour la librairie openszwave (déf = "./../plugins/configPath/")
            @ param userPath : chemin d'accès au répertoire de sauvegarde de la config openzwave et du log."
            @ param ozwlog (optionnel) : Activation du log d'openzawe, fichier OZW_Log.txt dans le répertoire user (déf = "--logging false")
        """
        self._xplPlugin = xplPlugin
        self._device = None
        self.monitorNodes = None
        self._log = log
        self._cb_send_xPL = cb_send_xPL
        self._cb_sendxPL_trig = cb_sendxPL_trig
        self._stop = stop
        self.pluginVers = self._xplPlugin.json_data['identity']['version']
        # Get config rest domogik
        self.conf_rest = {'rest_ssl_certificate': '', 'rest_server_ip': '127.0.0.1', 'rest_server_port': '40405', 'rest_use_ssl': 'False'}
        cfg_rest = Loader('rest')
        config_rest = cfg_rest.load()
        self.conf_rest = dict(config_rest[1])
        self._nodes = dict()
        self._pyOzwlibVersion =  'Unknown'
        self._configPath = configPath
        self._userPath = userPath
        self._initFully = False
        self._ctrlActProgress = None
        self.lastTest = 0
        self._completMsg = self._xplPlugin.get_config('cpltmsg')
        self._wsPort = int(self._xplPlugin.get_config('wsportserver'))
        self._device = self._xplPlugin.get_config('device')
        autoPath = self._xplPlugin.get_config('autoconfpath')
        user = pwd.getpwuid(os.getuid())[0]
        # Spécification du chemain d'accès à la lib open-zwave
        if autoPath :
            self._configPath = libopenzwave.configPath()
            if self._configPath is None :
                self._log.warning(u"libopenzwave can't autoconfigure path to config, try user config : {0}".format(configPath))
                self._configPath = configPath
        if not os.path.exists(self._configPath) : 
            self._log.error(u"Directory openzwave config not exist : %s" , self._configPath)
            raise OZwaveManagerException (u"Directory openzwave config not exist : %s"  % self._configPath)
        elif not os.access(self._configPath,  os.R_OK) :
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
        if not os.access(self._userPath,  os.W_OK) :
            self._log.error("User %s haven't write access on user openzwave directory : %s"  %(user,  self._userPath))
            raise OZwaveManagerException ("User %s haven't write access on user openzwave directory : %s"  %(user,  self._userPath))
        self._log.debug(u"Setting openzwave path for user : {0}".format(user))
        self._log.debug(u"     - Config path : {0}".format(self._configPath))
        self._log.debug(u"     - User path : {0}".format(self._userPath))
        # Séquence d'initialisation d'openzwave
        opt = ""
        self._ozwLog = ozwlog
        opts = "--logging true" if self._ozwLog else "--logging false"
        self._log.info(u"Try to run openzwave manager")
        self.options = libopenzwave.PyOptions(config_path =str(self._configPath), user_path=str(self._userPath))
        self.options.create(self._configPath, self._userPath,  opts)
        if self._completMsg: self.options.addOptionBool('NotifyTransactions',  self._completMsg)
        self.options.lock() # nécessaire pour bloquer les options et autoriser le PyManager à démarrer
        self._configPath = self.options.getOption('ConfigPath')  # Get real path through openzwave lib
        self._userPath = self.options.getOption('UserPath')        # Get real path through openzwave lib
        self._manager = libopenzwave.PyManager()
        self._manager.create()
        self._manager.addWatcher(self.cb_openzwave) # ajout d'un callback pour les notifications en provenance d'OZW.
        self._log.info(u" {0} -- plugin version : {1}".format(self.pyOZWLibVersion, self.pluginVers))
        self._log.info(u"   - Openzwave Config path : {0}".format(self._configPath))
        self._log.info(u"   - Openzwave User path : {0}".format(self._userPath))
        self._log.debug(u"   - Openzwave options : ")
        for opt in libopenzwave.PyOptionList.keys(): self._log.debug(u"       - {0} : {1}".format(opt, self.options.getOption(opt)))
        self.getManufacturers()
        # "List les devices de type primary.controler.""
        self._devicesCtrl = []
        self._openingDriver = None
        
        for a_device in self._xplPlugin.devices:
            self.addDeviceCtrl(a_device)
        if not self._devicesCtrl : 
            self._log.warning(u"No device primary.controller created in domogik, can't start openzwave driver.")
        self.starter = threading.Thread(None, self.startServices, "th_Start_Ozwave_Services", (), {})

     # On accède aux attributs uniquement depuis les property
    device = property(lambda self: self._device)
    nodes = property(lambda self: self._nodes)   
    totalNodeCount = property(lambda self: len(self._nodes))
    totalSleepingNodeCount = property(lambda self: self._getTotalSleepingNodeCount())
    totalNodeCountDescription = property(lambda self: self._getTotalNodeCountDescription())
    isReady = property(lambda self: self._getIfOperationsReady())
    pyOZWLibVersion = property(lambda self: self._getPyOZWLibVersion())

    def _getIfOperationsReady(self):
        """"Retourne True si toutes les conditions sont réunies pour faire des actions dans openzwave.
            Règle : au moins un controleur est ready avec sont node enregistré mais le _initFully pas obligatoirement"""
        ready =False
        for device in self._devicesCtrl:
            if device.ready and device.node is not None : 
                ready = True
                break
        return ready

    def startServices(self):
        """démarre les differents services (wsServer, monitorNodes, le controleurZwave.
            A appeler dans un thread à la fin de l'init du pluginmanager."""
        self._log.info("Start Ozwave services in 100ms...")
        self._stop.wait(0.1) # s'assurer que l'init du pluginmanager est achevé
        self.monitorNodes = ManageMonitorNodes(self)
        self.monitorNodes.start()  # demarrer la surveillance des nodes pour helper log
        # Ouverture du ou des controleurs principaux
        thOpen = threading.Thread(None, self.startOpenDevicesCtrl, "th_Start_open_drivers", (), {})
        thOpen.start()

    def startOpenDevicesCtrl(self):
        """Demarre les différents driver en attendant que le traitement driver précedent soit  terminé.
              (action nécéssaire parcequ'openzwave ne renvoi pas l'id du driver dans les notifications)
           A appeler dans un thread à la fin de l'init du pluginmanager."""
        for device in self._devicesCtrl:
            while self._openingDriver and not self._stop.isSet(): self._stop.wait(0.1)
            self.openDeviceCtrl(device)
        
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
        if dmgDevice['device_type_id'] == 'primary.controller' :
            driver = self._xplPlugin.get_parameter(dmgDevice, 'driver')
            if not self.getDeviceCtrl('driver',  driver) :
                networkID = self._xplPlugin.get_parameter_for_feature(dmgDevice, 'xpl_stats',  'ctrl_status',  'networkid')
                self._devicesCtrl.append(PrimaryController(driver, networkID, None))
                self._log.info(u"Domogik device primary controller registered : {0}".format(self._devicesCtrl[-1]))
            else : self._log.info("Device primary controller allready exist on {0}".format(driver))
            
    def removeDeviceCtrl(self, device):
       if device in self._devicesCtrl :
           self.closeDeviceCtrl(device)
           self._log.info(u"Domogik device primary controller removed : {0}".format(device))
           self._devicesCtrl.remove(device)

    def isNodeDeviceCtrl(self,  node):
        """Return le deviceCtrl si le node est un controleur primaire sinon None."""
        for device in self._devicesCtrl :
            if node == device.node : return device
        return None
    
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
    
    def openDeviceCtrl(self, device):
        """Ajoute un controleur au manager openzwave, le retire avant si nécessaire."""
        if device.status == 'open':
            self._log.info(u"Remove driver from openzwave :{0}".format(device.driver))
            self._manager.removeDriver(device.driver)
            self._stop.wait(2)
        self._log.info(u"Adding driver to openzwave : {0}".format(device.driver))
        self._cb_send_xPL({'type':'xpl-trig', 'schema':'ozwctrl.basic',
                    'data': {'type': 'status', 'networkid': device.networkID, 'status':'started', 'usrmsg': "Openzwave opening driver, init process ...",  'data': "None"}})
        self._manager.addDriver(device.driver)  # ajout d'un driver dans le manager
        device.status = 'open'
        self._openingDriver = device.driver
        
    def closeDeviceCtrl(self, device):
        """Ferme un controleur du manager openzwave"""
        if device.status == 'open' :
            self._log.info(u"Remove driver from openzwave : {0}".format(device.driver))
            self._manager.removeDriver(device.driver)
            device.status = 'close'
            device.ready = False
            self._xplPlugin.publishMsg('ozwave.ctrl.closed', {'node': 'controller', 'type': 'driver-remove', 'usermsg' : 'Driver removed.', 'data': False})
            self._cb_send_xPL({'type':'xpl-trig', 'schema':'ozwctrl.basic',
                            'data': {'type': 'status', 'networkid': device.networkID, 'status':'close', 'usrmsg': "Openzwave driver closed",  'data': "None"}})

    def stop(self):
        """ Stop class OZWManager."""
        self._log.info(u"Stopping plugin, Remove driver(s) from openzwave")
        for device in self._devicesCtrl : self.removeDeviceCtrl(device)
        self._xplPlugin.publishMsg('ozwave.manager.stopped',{'node': 'controller', 'type': 'driver-remove', 'usermsg' : 'Plugin stopped.', 'data': False})
        if self._xplPlugin. _ctrlHBeat: self._xplPlugin. _ctrlHBeat.stop()

    def sendXplCtrlState(self):
        """Envoi un hbeat de l'état des controleurs zwave sur le hub xPl"""
        for device in self._devicesCtrl:
            if device.status == 'open':
                if device.node is None : st = 'opening...'
                elif device.ctrlActProgress and device.ctrlActProgress.has_key('state') and device.ctrlActProgress['state'] == device.node.SIGNAL_CTRL_WAITING : st ='locked'
                elif device.ready : st= 'ok'
                else : st = 'init...'
                self._cb_send_xPL({'type':'xpl-trig', 'schema':'ozwctrl.basic',
                                    'data': {'type': 'status', 'networkid': device.networkID, 'status':st, 'usermsg': "None", 'data': "None"}})

    def getPluginInfo(self):
        """Renvoi les informations d'état et de connection du plugin."""
        ctrlReady = False
        for device in self._devicesCtrl:
        	if device.ready :
        		ctrlReady = True
        		break
        retval = {"hostport": self._wsPort, "ctrlready": ctrlReady}
        if self._initFully :
            retval["Init state"] = NodeStatusNW[2] # Completed
        else :
            retval["Init state"] = NodeStatusNW[3] # In progress - Devices initializing
        retval["error"] = ""
        return retval
    
    def getManufacturers(self):
        """"Renvoi la list (dict) de tous le fabriquants et produits reconnus par la lib openzwave."""
        self.manufacturers = Manufacturers(self._configPath)
        
    def getAllProducts(self):
        """"Renvoi la list (dict) de tous le fabriquants et produits reconnus par la lib openzwave."""
        if self.manufacturers :
            return self.manufacturers.getAllProductsName()
        else :
            return {error: 'Manufacturers xml file not loaded.'}
        
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
        tplugin = sys.getsizeof(self) + sum(sys.getsizeof(v) for v in self.__dict__.values()) + self._xplPlugin.getsize()
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
                    # TODO : voir coté device_detected ce qu'il est possible de faire
                    ctrlNodeID = 0
                else : ctrlNodeID = ctrl.nodeID
                if nodeId == ctrlNodeID :
                    retval = ZWaveController(self,  homeId, nodeId,  True,  ctrl.networkID)
                    self._log.info("Node %d is affected as primary controller)", nodeId)
                    ctrl.node = retval
                    retval.reportChangeToUI({'node': 'controller', 'type': 'init-process', 'usermsg' : 'Zwave network initialization process could take several minutes. ' +
                                                ' Please be patient...', 'data': NodeStatusNW[3]})
                    # TODO: Voir comment gérer les controler secondaire, type ZWaveNode ou ZWaveController ?
#                            self._log.info("A primary controller allready existing, node %d id affected as secondary.", nodeId)
#                            retval = ZWaveController(self, homeId, nodeId,  False)
                else : 
                    retval = ZWaveNode(self,  homeId, nodeId)
                self._log.info('Created new node with homeId 0x%0.8x, nodeId %d', homeId, nodeId)
                self._nodes[ref] = retval
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
#         DriverReset = 20                  / All nodes and values for this driver have been removed.  This is sent instead of potentially hundreds of individual node and value notifications.
#         EssentialNodeQueriesComplete = 21 / The queries on a node that are essential to its operation have been completed. The node can now handle incoming messages.
#         NodeQueriesComplete = 22          / All the initialisation queries on a node have been completed.
#         AwakeNodesQueried = 23            / All awake nodes have been queried, so client application can expected complete data for these nodes.
#         AllNodesQueriedSomeDead = 24      / All nodes have been queried but some dead nodes found.
#         AllNodesQueried = 25              / All nodes have been queried, so client application can expected complete data.
#         Notification = 26                        / An error has occured that we need to report.
#         DriverRemoved = 27                 / The Driver is being removed. (either due to Error or by request) Do Not Call Any Driver Relatedh -- see rev : ttps://code.google.com/p/open-zwave/source/detail?r=890


#TODO: notification à implémenter
#         ValueRefreshed = 3                / A node value has been updated from the Z-Wave network.
#         SceneEvent = 13                 / Scene Activation Set received
#         CreateButton = 14                 / Handheld controller button event created 
#         DeleteButton = 15                 / Handheld controller button event deleted 
#         ButtonOn = 16                     / Handheld controller button on pressed event
#         ButtonOff = 17                    / Handheld controller button off pressed event 

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
            self._openingDriver = ""
            self._log.info(u"Driver {0} ready. homeId is {1}, controller node id is {2}, using {3} library version {4}".format(ctrl.driver,
                                                                                                                                                                                           self.matchHomeID(ctrl.homeId), 
                                                                                                                                                                                           ctrl.nodeID, ctrl.libraryTypeName, ctrl.libraryVersion))
            self._log.info(u"OpenZWave Initialization Begins.")
            self._xplPlugin.publishMsg('ozwave.ctrl.state', {'node': 'controller', 'type': 'driver-ready', 'usermsg' : 'Driver is ready.', 'data': True})
            self._cb_send_xPL({'type':'xpl-trig', 'schema':'ozwctrl.basic',
                                           'data': {'type': 'status', 'networkid': ctrl.networkID, 'status':'init...', 'usrmsg': "Openzwave opening driver, init process ...",  'data': "None"}})

    def _handleDriverReset(self, args):
        """ Le driver à été recu un reset, tous les nodes, sauf le controlleur, sont détruis."""
        ctrl = self.getDeviceCtrl('homeID', args['homeId']) # TODO: vérifier si args retourne le driver ou homeId
        if ctrl is not None :
            ctrl.ready = false
            for n in self._nodes:
                if (self._nodes[n] != ctrl.node) and (self._nodes[n].homeId == ctrl.homeId) :
                    node = self._nodes.pop(n)
                    del(node)
            self._log.info(u"Driver {0}, homeId {1} is reset, all network nodes deleted".format(ctrl.driver, args))
            self._xplPlugin.publishMsg('ozwave.ctrl.state', {'node': 'controller', 'type': 'driver-reset', 'usermsg' : 'Driver reseted, All nodes must be recovered.', 'data': False})
            self._cb_send_xPL({'type':'xpl-trig', 'schema':'ozwctrl.basic',
                            'data': {'type': 'status', 'networkid': ctrl.networkID, 'status':'reseted', 'usrmsg': "Openzwave driver reseted, All nodes must be recovered.",'data': "None"}})
        else :
            self._log.warning(u"A driver reset is recieved but not domogik controller attached, all nodes deleted. Notification : {1}".format(args))
            self._xplPlugin.publishMsg('ozwave.ctrl.state', {'node': 'controller', 'type': 'driver-reset', 'usermsg' : 'Driver reseted but not registered, All nodes must be recovered.', 'data': args})
            self._cb_send_xPL({'type':'xpl-trig', 'schema':'ozwctrl.basic',
                            'data': {'type': 'status', 'networkid': 'unknown', 'status':'reseted', 'usrmsg': "Driver reseted but not registered, All nodes must be recovered.",'data': "None"}})
            self._nodes = None
            
    def _handleDriverRemoved(self,  args):
        """ Le driver à été arrêter et supprimer, tous les nodes sont détruis."""
        ctrl = self.getDeviceCtrl('homeID', args['homeId']) # TODO: vérifier si args retourne le driver ou homeId
        if ctrl is not None :
            ctrl.ready = false
            ctrl.status = 'close'
            for n in self._nodes:
                if self._nodes[n].homeId == ctrl.homeId :
                    node = self._nodes.pop(n)
                    del(node)
            self._log.info(u"Driver {0}, homeId {1} is removed, all network nodes deleted".format(ctrl.driver, args))
            self._xplPlugin.publishMsg('ozwave.ctrl.state', {'node': 'controller', 'type': 'driver-remove', 'usermsg' : 'Driver removed, All nodes deleted.', 'data': False})
            self._cb_send_xPL({'type':'xpl-trig', 'schema':'ozwctrl.basic',
                            'data': {'type': 'status', 'networkid': ctrl.networkID, 'status':'removed', 'usrmsg': "Openzwave driver removed, All nodes deleted.",'data': "None"}})
            self._devicesCtrl.pop(ctrl)
            del (ctrl)
        else :
            self._log.warning(u"A driver removed is recieved but not domogik controller attached, all nodes deleted. Notification : {1}".format(args))
            self._xplPlugin.publishMsg('ozwave.ctrl.state', {'node': 'controller', 'type': 'driver-remove', 'usermsg' : 'Driver removed but not registered, All nodes deleted.', 'data': args})
            self._cb_send_xPL({'type':'xpl-trig', 'schema':'ozwctrl.basic',
                            'data': {'type': 'status', 'networkid': 'unknown', 'status':'removed', 'usrmsg': "Driver removed but not registered, All nodes deleted.",'data': "None"}})
            self._devicesCtrl = None
            self._nodes = None
                    
    def _handleDriverFailed(self, args):
        """L'ouverture du driver à échoué.."""
        ctrl = self.getDeviceCtrl('driver', self._openingDriver)
        self._openingDriver = ""
        ctrl.status = 'close'
        ctrl.ready = False
        self._log.error(u"Openzwave fail to open driver {0}, ozw message : {1}".format(ctrl.driver, args))
        self._xplPlugin.publishMsg('ozwave.ctrl.state', {'node': 'controller', 'type': 'driver-failed', 'usermsg' : "Openzwave opening driver {0} fail.".format(ctrl.driver), 'data': True})
        self._cb_send_xPL({'type':'xpl-trig', 'schema':'ozwctrl.basic',
                                       'data': {'type': 'status', 'networkid': ctrl.networkID, 'status':'fail', 'usrmsg': "Openzwave opening driver {0} fail.".format(ctrl.driver),  'data': "None"}})

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
                node._updateConfig()
        self._log.debug(u"End of process initialization complete")
        ctrl.ready = True
        self._initFully = True
        ctrl.node.reportChangeToUI({'node': 'controller', 'type': 'init-process', 'usermsg' : 'Zwave network Initialized.', 'data': NodeStatusNW[2]})
        self._cb_send_xPL({'type':'xpl-trig', 'schema':'ozwctrl.basic',
                                    'data': {'type': 'status', 'networkid': ctrl.networkID, 'status':'ok'}})
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
                self._log.info('Z-Wave Controller Node {0} is ready, UI dialogue autorised.'.format(self.refNode(ctrl.homeId, node.nodeId)))
        else :
            if args['nodeId'] == 255 and not self._initFully :
                self._handleInitializationComplete(args) # TODO :depuis la rev 585 pas de 'AwakeNodesQueried' ou  'AllNodesQueried' ? on force l'init
    
    def _handleMarkSomeNodesDead(self,  args):
        """Un ou plusieurs node(s) ont été identifié comme mort"""
        self._log.info("Some nodes ares dead : " , args)
        print "**************************************"
        print ("Some nodes ares dead : " , args)
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
        print nCode,  nCode.doc
        if not node:
            self._log.debug("Notification for node who doesn't exist : {0}".format(args))
        else :
            if nCode == 'MsgComplete':     #      Code_MsgComplete = 0,                                   /**< Completed messages */
                print 'MsgComplete notification code :', args
                self._log.debug('MsgComplete notification code for Node {0}.'.format(node.refName))
                node.receivesCompletMsg(args)
            elif nCode == 'Timeout':         #      Code_Timeout,                                              /**< Messages that timeout will send a Notification with this code. */
                print 'Timeout notification on node :',  args['nodeId']
                self._log.info('Timeout notification code for Node {0}.'.format(args['nodeId']))
            elif nCode == 'NoOperation':  #       Code_NoOperation,                                       /**< Report on NoOperation message sent completion  */
                print 'NoOperation notification code :', args
                self._log.info('Z-Wave Device Node {0} successful receipt testing message.'.format(node.refName))
                node.receivesNoOperation(args,  self.lastTest)
            elif nCode == 'Awake':            #      Code_Awake,                                                /**< Report when a sleeping node wakes up */
                node.setSleeping(False)
                print ('Z-Wave sleeping device Node {0} wakes up.'.format(node.refName))
                self._log.info('Z-Wave sleeping device Node {0} wakes up.'.format(node.refName))
            elif nCode == 'Sleep':            #      Code_Sleep,                                                /**< Report when a node goes to sleep */
                node.setSleeping(True)
                node.receiveSleepState(args)
                print ('Z-Wave Device Node {0} goes to sleep.'.format(node.refName))
                self._log.info('Z-Wave Device Node {0} goes to sleep.'.format(node.refName))
            elif nCode == 'Dead':             #       Code_Dead                                               /**< Report when a node is presumed dead */
                node.markAsFailed()
                print ('Z-Wave Device Node {0} marked as dead.'.format(node.refName))
                self._log.info('Z-Wave Device Node {0} marked as dead.'.format(node.refName))
            elif nCode == 'Alive':             #       Code_Alive						/**< Report when a node is revived */
                node.markAsOK()
                print ('Z-Wave Device Node {0} marked as alive.'.format(node.refName))
                self._log.info('Z-Wave Device Node {0} marked as alive.'.format(node.refName))
            else :
                self._log.error('Error notification code unknown : ', args)

    def _handlePollingDisabled(self, args):
        """le polling d'une value commande classe a été désactivé."""
        self._log.info('Node {0} polling disabled.'.format(args['nodeId']))
        data = {'polled': False}
    #    data['id'] = str(args['valueId']['id'])
        self._xplPlugin.publishMsg('ozwave.node.poll', {'node': args['nodeId'], 'notifytype': 'polling', 'usermsg' : 'Polling disabled.', 'data': data})
        
    def _handlePollingEnabled(self, args):
        """le polling d'une value commande classe à été activé."""
        self._log.info('Node {0} polling enabled.'.format(args['nodeId']))
        data = {'polled': True}
     #   data['id'] = str(args['valueId']['id'])
        self._xplPlugin.publishMsg('ozwave.node.poll', {'node': args['nodeId'], 'notifytype': 'polling', 'usermsg' : 'Polling enabled.', 'data': data})

    def _handleNodeChanged(self, args):
        """Un node est ajouté ou a changé"""
        node = self._fetchNode(args['homeId'], args['nodeId'])
        node._lastUpdate = time.time()
        self._log.info(u"Node {0} as add or changed (homeId {1})".format(args['nodeId'], self.matchHomeID(args['homeId'])))
        
    def _handleNodeRemoved(self, args):
        """Un node est ajouté ou a changé"""
        node = self._getNode(args['homeId'], args['nodeId'])
        if node :
            ctrl = self.isNodeDeviceCtrl(node)
            if ctrl : self.removeDeviceCtrl(ctrl)
            self._nodes.pop(self.refNode(node.homeId, node.nodeId))
      #      node.__del__()
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
        valueNode.updateData(valueId)
        # formatage infos générales
        # ici l'idée est de passer tout les valeurs stats et trig en identifiants leur type par le label forcé en minuscule.
        # les labels sont listés le fichier json du plugin.
        # Le traitement pour chaque command_class s'effectue dans la ValueNode correspondante.
        msgtrig = valueNode.valueToxPLTrig()
        if msgtrig : self._cb_sendxPL_trig(msgtrig)
        else : print ('Value non implémentee vers xPL : %s'  % valueId['commandClass'] )

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
        
    def handle_ControllerAction(self,  networkId,  action):
        """Transmet une action controleur a un controleur primaire."""
        print ('********************** handle_ControllerAction ***********')
        print 'Action : ',  action
        if self.isReady :
            ctrl = self.getCtrlOfNetwork(networkId)
            crtl.ctrlActProgress = action   
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
        """Transmmet le hard resset au controleur primaire."""
        # TODO: Pour l'instant l"action ne contient pas l'ID du controleur, On lance l'action sur le premier. Mettre l'ID dans l'action
        retval = {'error': ''}
        if self.isReady :
            ctrl = self.getCtrlOfNetwork(networkId)
            if not ctrl.node.hard_reset() :
                retval['error'] = 'No reset for secondary controller'
        else : retval['error'] = 'Controller node ready'
        return retval
       
    def getNetworkInfo(self, networkId):
        """ Retourne les infos principales du réseau zwave (dict) """
        retval = {}
        retval["ConfigPath"] = self._configPath
        retval["UserPath"] = self._userPath
        retval["PYOZWLibVers"] = self.pyOZWLibVersion
        retval["OZWPluginVers"] = self.pluginVers
        # TODO: Gére plusieurs networdID dans les fonction qui appellent.
        retval["Controllers"] = []
        if self.isReady:
            for ctrl in self._devicesCtrl:
                ctrlInfos = dict()
                ctrlInfos["NetworkID"] = ctrl.networkID
                ctrlInfos["HomeID"] = self.matchHomeID(ctrl.homeId)
                if ctrl.ready :
                    ctrlInfos["Model"] = "{0} -- {1}".format(ctrl.node.manufacturer, ctrl.node.product)
                    ctrlInfos["Protocol"] = self._manager.getControllerInterfaceType(ctrl.homeId)
                    ctrlInfos["Primary controller"] = ctrl.getControllerDescription()
                    ctrlInfos["Node"] = ctrl.node.nodeId
                    ctrlInfos["Library"] = ctrl.libraryTypeName
                    ctrlInfos["Version"] = ctrl.libraryVersion
                    ctrlInfos["Node count"] = ctrl.getNodeCount()
                    ctrlInfos["Node sleeping"] = ctrl.getSleepingNodeCount()
                    ctrlInfos["Poll interval"] = ctrl.node.getPollInterval()
                    ctrlInfos["ListNodeId"] = ctrl.getNodesId()
                else:
                    ctrlInfos["Model"] = "Controller not find, wait or check configuration and hardware."
                retval["Controllers"].append(ctrlInfos)
            if self._initFully :
                retval["Init state"] = NodeStatusNW[2] #Completed
                retval["state"] = "alive"
            else :
                retval["Init state"] = NodeStatusNW[3] #In progress - Devices initializing
                retval["state"] = "starting "
            retval["error"] = ""
            print'**** getNetworkinfo : ',  retval
            return retval
        else : 
            retval["error"] = "Zwave network not ready, be patient..."
            retval["Init state"] = NodeStatusNW[0] # Uninitialized
            retval["state"] = "not-configured"
            return retval
        
    def getZWRefFromxPL(self, xplParams):
        """ Retourne  les références Zwave envoyées depuis le xPL domogik 
            @param : xplParams format : dict avec le référence du device """
        retval = {}
        if "networkid" in xplParams :
            retval['homeId'] = self.getHomeID(xplParams["networkid"])
        if "node" in xplParams :
            retval['nodeId'] = int(xplParams['node'])
        if "instance" in xplParams :
            retval['instance'] = int(xplParams['instance'])
        if not retval or retval['homeId'] is None :
            self._log.warning(u"xPL message doesn't refer a node : {0}".format(xplParams))
            retval = None
        return retval
        
    def getxPLRefFromZW(self, device):
        """ Retourne les réferences xPL d'adressage d'un device domogik.
            @param : device : une des class ZWaveController, ZWaveNode ou ZWaveValueNode """
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
        
    def sendNetworkZW(self, device, command,  value):
        """Principalement en provenance du réseaux xPL
              Envoie la commande sur le réseaux zwave
            @param : device = dict{'homeId', 'nodeId', 'instance'}
        """ 
        print ("envoi zwave command %s" % command)
        if device != None :
            node = self._getNode(device['homeId'],  device['nodeId'])
            if node : node.sendCmdBasic(device['instance'], command, value)

    def getNodeInfos(self, homeId, nodeId):
        """ Retourne les informations d'un device, format dict{} """
        if self.isReady :
            node = self._getNode(homeId,  nodeId)
            if node : return node.getInfos()
            else : return {"error" : "Unknown Node : {0}".format(node.refName)}
        else : return {"error" : "Zwave network not ready, can't find node %{0}".format(node.refName)}
        
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
        """Retourne la liste des type de value possible et la doc"""
        retval = {}
        for elem in  libopenzwave.PyValueTypes :
            retval[elem] = elem.doc
        return retval

    def testNetwork(self, networkId, count = 1, timeOut = 10000,  allReport = False):
        """Envois une serie de messages à tous les nodes pour tester la réactivité du réseaux."""
        ctrl = self.getCtrlOfNetwork(networkId)
        if ctrl is None : return {"error" : "Zwave network not ready, can't find controller"}
        if ctrl.node is None : return {"error" : "Zwave network not ready, can't find node controller"}
        if ctrl.ready :
            for node in self._nodes.itervalues() :
                if (node.homeId == ctrl.homeId) and (not node.isSleeping) and (self.isNodeDeviceCtrl(node)) is None :
                    error = node.trigTest(count, timeOut,  allReport,  False)
                    if error['error'] != '' :  retval['error'] = retval['error'] +'/n' + error['error']
            self.lastTest = time.time()
            self._manager.testNetwork(ctrl.homeId, count)
            if retval['error']  != '': retval['error'] = 'Some node(s) have error :/n' + retval['error']
            return retval
        else : return {"error" : "Zwave network not ready, can't find controller."}

    def testNetworkNode(self, homeId, nodeId, count = 1, timeOut = 10000,  allReport = False):
        """Envois une serie de messages à un node pour tester sa réactivité sur le réseaux."""
        ctrl = self.getCtrlOfNetwork(homeId)
        if ctrl is None : return {"error" : "Zwave network not ready, can't find controller"}
        if ctrl.ready :
            node = self._getNode(homeId,  nodeId)
            if self.isNodeDeviceCtrl(node) is None :
                if node : retval = node.testNetworkNode(count, timeOut,  allReport)
                else : retval['error'] = "Zwave node {0} unknown.".format(node.refName)
            else : retval['error'] = "Can't test primary controller, node {0}.".format(node.refName)
            return retval
        else : return {"error" : "Zwave network not ready, can't find node {0}".format(node.refName)}

    def healNetwork(self, networkId, upNodeRoute):
        """Tente de 'réparé' des nodes pouvant avoir un problème. Passe tous les nodes un par un"""
        ctrl = self.getCtrlOfNetwork(networkId)
        if ctrl is None : return {"error" : "Zwave network not ready, can't find controller"}
        if ctrl.ready :
            self._manager.healNetwork(ctrl.homeId, upNodeRoute)

    def healNetworkNode(self, homeId, nodeId, upNodeRoute):
        """Tente de 'réparé' un node particulier pouvant avoir un problème."""
        ctrl = self.getCtrlOfNetwork(homeId)
        if ctrl is None : return {"error" : "Zwave network not ready, can't find controller"}
        if ctrl.ready :
            node = self._getNode(homeId,  nodeId)
            if node : self._manager.healNetworkNode(ctrl.homeId, nodeId, upNodeRoute)

    def getGeneralStatistics(self, networkId):
        """Retourne les statistic générales du réseaux"""
        retval={}
        ctrl = self.getCtrlOfNetwork(networkId)
        if ctrl is None : return {"error" : "Zwave network not ready, can't find controller"}
        if ctrl.node is None : return {"error" : "Zwave network not ready, can't find node controller"}
        if ctrl.ready :
            retval = ctrl.node.stats()
            if retval : 
                for  item in retval : retval[item] = str (retval[item]) # Pour etre compatible avec javascript
                retval['error'] = ""
            else : retval = {'error' : "Zwave controller not response."}
            retval['msqueue'] = str(self.getCountMsgQueue(ctrl.homeId))
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
                except Exception as e:
                    self._log.error('node.setName() :' + e.message)
                    return {"error" : "Node %d, can't update name, error : %s" %(nodeId, e.message) }
            if newloc != 'Undefined' and node.location != newloc :
                try :
                    node.setLocation(newloc)
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
              #      print ('SetValue, relecture de la valeur : ',  value.getOZWValue())
                    return retval
                else : return {"value": newValue, "error" : "Unknown value : %d" %valId}
            else : return {"error" : "Unknown Node : %d" % nodeId}
        else : return {"value": newValue, "error" : "Zwave network not ready, can't find value %d" %valId}     

    def setMembersGrps(self,  homeId, nodeId,  newGroups):
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

    def cb_ServerWS(self, message):
        """Callback en provenance de l'UI via server Websocket (resquest avec ou sans ack)"""
        blockAck = False
        report = {'error':  'Message not handle.'}
        ackMsg = {}
        print "WS - Requete UI",  message
        if message.has_key('header') :
            if message['header']['type'] in ('req', 'req-ack'):
            # TODO: Pour l'instant la requete ne contient pas l'ID du controleur, On lance l'action sur le premier. Mettre l'ID dans la requete
                if not 'homeId' in message : message['homeId'] = self._devicesCtrl[0].homeId                
                if not 'networkId' in message : message['networkId'] = self.getNetworkID(message['homeId'])
            # Fin solution temporaire
                ctrl = self.getCtrlOfNetwork(message['networkId'])
                if message['request'] == 'ctrlAction' :
                    report = self.handle_ControllerAction(message['networkId'],  message['action'])
             #       if message['action']['cmd'] =='getState' and report['cmdstate'] != 'stop' : blockAck = True
                elif message['request'] == 'ctrlSoftReset' :
                    report = self.handle_ControllerSoftReset(message['networkId'])
                elif message['request'] == 'ctrlHardReset' :
                    report = self.handle_ControllerHardReset(message['networkId'])
                elif message['request'] == 'GetNetworkID' :
                    report = self.getNetworkInfo(message['networkId'])
                elif message['request'] == 'GetNodeInfo' :
                    if self._IsNodeId(message['node']):
                        report = self.getNodeInfos(message['homeId'], message['node'])
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                    print "Refresh node :", report
                elif message['request'] == 'RefreshNodeDynamic' :
                    if self._IsNodeId(message['node']):
                        report = self.refreshNodeDynamic(message['homeId'], message['node'])
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                elif message['request'] == 'RefreshNodeInfo' :
                    if self._IsNodeId(message['node']):
                        report = self.refreshNodeInfo(message['homeId'], message['node'])
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                elif message['request'] == 'RefreshNodeState' :
                    if self._IsNodeId(message['node']):
                        report = self.refreshNodeState(message['homeId'], message['node'])
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                    print "Refresh node :", report
                elif message['request'] == 'HealNode' :
                    if self._IsNodeId(message['node']):
                        self.healNetworkNode(message['networkId'],  message['node'],  message['forceroute'])
                        report = {'usermsg':'Command sended, please wait for result...'}
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                elif message['request'] == 'HealNetwork' :
                    self.healNetwork(message['networkId'], message['forceroute'])
                    report = {'usermsg':'Command sended node by node, please wait for each result...'}
                elif message['request'] == 'SaveConfig':
                    report = self.saveNetworkConfig()
                elif message['request'] == 'GetMemoryUsage':
                    report = self.getMemoryUsage()
                elif message['request'] == 'GetAllProducts':
                    report = self.getAllProducts()
                elif message['request'] == 'SetNodeNameLoc':
                    report = self.setUINodeNameLoc(message['homeId'], message['node'], message['newname'],  message['newloc'])
                    ackMsg['node'] = message['node']
                elif message['request'] == 'GetNodeValuesInfo':
                    if self._IsNodeId(message['node']):
                        report =self.getNodeValuesInfos(message['node'])
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                elif message['request'] == 'GetValueInfos':
                    if self._IsNodeId(message['node']):
                        valId = long(message['valueid']) # Pour javascript type string
                        report =self.getValueInfos(message['node'], valId)
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                    ackMsg['valueid'] = message['valueid']
                    print 'Refresh one Value infos : ', report
                elif message['request'] == 'SetPollInterval':
                    ctrl.node.setPollInterval(message['interval'],  False)
                    ackMsg['interval'] = ctrl.node.getPollInterval()
                    if  ackMsg['interval'] == message['interval']:
                        report = {'error':''}
                    else :
                        report = {'error':'Setting interval error : keep value %d ms.' %ackMsg['interval']}
                elif message['request'] == 'EnablePoll':
                    valId = long(message['valueid']) # Pour javascript type string
                    report = ctrl.node.enablePoll(message['node'],  valId,  message['intensity']) 
                    ackMsg['node'] = message['node']
                    ackMsg['valueid'] = message['valueid']
                elif message['request'] == 'DisablePoll':
                    valId = long(message['valueid']) # Pour javascript type string
                    report = ctrl.node.disablePoll(message['node'],  valId)
                    ackMsg['node'] = message['node']
                    ackMsg['valueid'] = message['valueid']
    
                elif message['request'] == 'GetValueTypes':
                    report = self.getValueTypes()  
                elif message['request'] == 'GetListCmdsCtrl':
                    report = self.getListCmdsCtrl(message['networkId'])
                elif message['request'] == 'setValue':
                    if self._IsNodeId(message['node']):
                        valId = long(message['valueid']) # Pour javascript type string
                        report = self.setValue(message['homeId'], message['node'], valId, message['newValue'])
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                    ackMsg['valueid'] = message['valueid']
                    print 'Set command_class Value : ',  report
                elif message['request'] == 'setGroups':
                    if self._IsNodeId(message['node']):
                        report = self.setMembersGrps(message['homeId'], message['node'], message['ngrps'])
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']         
                    print 'Set Groups association : ',  report
                elif message['request'] == 'GetGeneralStats':
                    report = self.getGeneralStatistics(message['networkId'])
                    print 'Refresh generale stats : ',  report
                elif message['request'] == 'GetNodeStats':
                    if self._IsNodeId(message['node']):
                        report = self.getNodeStatistics(message['homeId'], message['node']) 
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                    print 'Refresh node stats : ',  report
                elif message['request'] == 'StartCtrl':
                    if ctrl.status != 'open' :
                        self.openDeviceCtrl(ctrl)
                        report = {'error':'',  'running': True}
                    else : report = {'error':'Driver already running. For restart stop it before',  'running': True}
                    print 'Start Driver : ',  report
                elif message['request'] == 'StopCtrl':
                    if ctrl.status =='open' :
                        self.closeDeviceCtrl(ctrl)
                        report = {'error':'',  'running': False}
                    else : report = {'error':'No Driver knows.',  'running': False}
                    print 'Stop Driver : ',  report
                elif message['request'] == 'TestNetwork':
                    report = self.testNetwork(message["networkId"], message['count'],  10000, True)
                elif message['request'] == 'TestNetworkNode':
                    if self._IsNodeId(message['node']):
                        report = self.testNetworkNode(message["homeId"], message['node'],  message['count'],  10000, True)
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                elif message['request'] == 'GetLog':
                    report = self.getLoglines(message)
                elif message['request'] == 'GetLogOZW':
                    report = self.getLogOZWlines(message)
                elif message['request'] == 'StartMonitorNode':
                    if self._IsNodeId(message['node']):
                        report = self.monitorNodes.startMonitorNode(message["homeId"], message['node'])
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                elif message['request'] == 'StopMonitorNode':
                    if self._IsNodeId(message['node']):
                        report = self.monitorNodes.stopMonitorNode(message["homeId"], message['node'])
                    else : report = {'error':  'Invalide nodeId format.'}
                    ackMsg['node'] = message['node']
                else :
                    report['error'] ='Unknown request.'
                    print "commande inconnue"
            # probablement  a supprimer
#            if message['header']['type'] == 'req-ack' and not blockAck :
#                ackMsg['header'] = {'type': 'ack',  'idws' : message['header']['idws'], 'idmsg' : message['header']['idmsg'],
#                                               'ip' : message['header']['ip'] , 'timestamp' : long(time.time()*100)}
#                ackMsg['request'] = message['request']
#                if report :
#                    if 'error' in report :
#                        ackMsg['error'] = report['error']
#                    else :
#                        ackMsg['error'] = ''
#                    ackMsg['data'] = report
#                else : 
#                    ackMsg['error'] = 'No data report.'
#                self.serverUI.sendAck(ackMsg)   TODO: A supprimer après implantation de la MQ qui utilise le contenu de report
            return report
        else :
            raise OZwaveManagerException("WS request bad format : {0}".format(message))

    def reportCtrlMsg(self, networkId, ctrlmsg):
        """Un message de changement d'état a été recu, il est reporté au besoin sur le hub xPL pour l'UI
            SIGNAL_CTRL_NORMAL = 'Normal'                   # No command in progress.  
            SIGNAL_CTRL_STARTING = 'Starting'             # The command is starting.  
            SIGNAL_CTRL_CANCEL = 'Cancel'                   # The command was cancelled.
            SIGNAL_CTRL_ERROR = 'Error'                       # Command invocation had error(s) and was aborted 
            SIGNAL_CTRL_WAITING = 'Waiting'                # Controller is waiting for a user action.  
            SIGNAL_CTRL_SLEEPING = 'Sleeping'              # Controller command is on a sleep queue wait for device.  
            SIGNAL_CTRL_INPROGRESS = 'InProgress'       # The controller is communicating with the other device to carry out the command.  
            SIGNAL_CTRL_COMPLETED = 'Completed'         # The command has completed successfully.  
            SIGNAL_CTRL_FAILED = 'Failed'                     # The command has failed.  
            SIGNAL_CTRL_NODEOK = 'NodeOK'                   # Used only with ControllerCommand_HasNodeFailed to indicate that the controller thinks the node is OK.  
            SIGNAL_CTRL_NODEFAILED = 'NodeFailed'       # Used only with ControllerCommand_HasNodeFailed to indicate that the controller thinks the node has failed.
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
        print 'reportCtrlMsg', ctrlmsg
        if ctrlmsg['state'] == ctrl.node.SIGNAL_CTRL_FAILED :
            node = self._getNode(networkId, ctrlmsg['nodeid']) 
            if node : node.markAsFailed();
        if ctrlmsg['state'] == ctrl.node.SIGNAL_CTRL_NODEOK :
            node = self._getNode(networkId, ctrlmsg['nodeid']) 
            if node : node.markAsOK()
        if ctrlmsg['state'] in [ctrl.node.SIGNAL_CTRL_NORMAL,  ctrl.node.SIGNAL_CTRL_CANCEL,
                                        ctrl.node.SIGNAL_CTRL_ERROR,  ctrl.node.SIGNAL_CTRL_COMPLETED,  
                                        ctrl.node.SIGNAL_CTRL_FAILED, ctrl.node.SIGNAL_CTRL_NODEOK] :
            report['cmdstate'] = 'stop'                                            
            ctrl.ctrlActProgress= None   
        else :
            report['cmdstate'] = 'waiting'
        msg = {'notifytype': 'ctrlstate'}
        msg['data'] = report
        self._xplPlugin.publishMsg('ozwave.ctrl.state', msg)

class PrimaryController():
    """Objet de liaison entre un device domogik un controleur primaire zwave.
        La class mémorise et compile des informations sur le controleur primaire et son réseaux de nodes,
        mais ne fait aucune action dans la lib openzwave. Celle-ci sont faite dans le manager OZWavemanager
        ou dans le node controleur ZWaveController.
    """
    
    def __init__(self,  driver,  networkID,  homeId = None):
        """Initialisation """
        self.driver = driver
        self.networkID = networkID
        self.homeId = homeId
        self.status = 'close'
        self.ready = False
        self.ctrlActProgress = None
        self.node = None
        self.nodeId = 0
        self.libraryVersion = "Unknown"
        self.libraryTypeName = "Unknown"
        self.timeStarted = 0
        self.controllercaps = None

    def __str__(self):
        return u"driver = {0}, networkID = {1}, homeId = {2}, status = {3}, ready = {4}".format(self.driver, self.networkID , self.homeId, self.status, self.ready)

	def getCountMsgQueue(self):
		"""Retourne le nombre de message
		:return: The count of messages in the outgoing send queue.
		:rtype: int
		"""
		if self.node is not None :
			return self.node._manager.getSendQueueCount(self.homeId)
		return 0

    def saveNetworkConfig(self):
        """Enregistre le configuration au format xml"""
        retval = {}
        if self.node is not None :
            self._manager.writeConfig(self.homeId)
            print "config sauvée"
            retval["File"] = "confirmed"
        return retval

	def getListCmdsCtrl(self):
		"""Retourne le liste des commandes possibles du controleur ainsi que la doc associée."""
		retval = {}
		if self.node is None : return {"error" : "Zwave network not ready, can't find node controller"}
		if ctrl.ready :
			retval = self.node.cmdsAvailables()
			retval['error'] = ""
			return retval
		else : return {"error" : "Zwave network not ready, can't controller get command list."}

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

    def getNodes(self):
        """ Renvoi la liste des nodes du reseaux."""
        retval = []
        if self.node is not None :
            for node in self.node._ozwmanager._nodes.itervalues():
                if node.homeId == self.homeId:
                    retval.append(node)
        return retval

    def getNodesId(self):
        """ Renvoi la liste des nodes du reseaux."""
        retval = []
        if self.node is not None :
            for node in self.node._ozwmanager._nodes.itervalues():
                if node.homeId == self.homeId:
                    retval.append(node.nodeId)
        return retval
        
    def getNodeCount(self):
        """Renvoi le nombre de node du reseaux."""
        retval = 0
        if self.node is not None :
            for node in self.node._ozwmanager._nodes.itervalues():
                if node.homeId == self.homeId:
                    retval += 1
        return retval

    def getSleepingNodeCount(self):
        """Renvoi le nombre de node du reseaux en veille."""
        retval = 0
        if self.node is not None :
            for node in self.node._ozwmanager._nodes.itervalues():
                if node.homeId == self.homeId and node.isSleeping:
                    retval += 1
        return retval
   
    def getFailedNodeCount(self):
        """Renvoi le nombre de node du reseaux considere HS."""
        retval = 0
        if self.node is not None :
            for node in self.node._ozwmanager._nodes.itervalues():
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
        
