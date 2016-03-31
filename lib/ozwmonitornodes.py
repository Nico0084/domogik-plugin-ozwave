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

import threading
from datetime import datetime
from ozwdefs import *
from collections import deque
import pprint
from tailer import Tailer
import os
import traceback

class OZwaveMonitorNodeException(OZwaveException):
    """"Zwave monitor node manager exception  class"""

    def __init__(self, value):
        OZwaveException.__init__(self, value)
        self.msg = "OZwave monitor node exception:"

class ManageMonitorNodes(threading.Thread):
    """Monitor Node manager"""

    def __init__(self, ozwManager):
        """Create node(s) watch instance."""
        threading.Thread.__init__(self)
        self.name = "Manage_Monitor_Nodes"
        self._ozwManager = ozwManager
        self.nodesMonitor={}
        self.__reports = deque([])
        self._pluginLog = ozwManager._log
        self._stop = ozwManager._stop
        self._running = False
        self._pluginLog.info(u'Monitor node(s) manager is initialized.')

    hasMonitored = property(lambda self: True if self.nodesMonitor != {} else False)

    def refNode(self, homeId, nodeId):
        return self._ozwManager.refNode(homeId, nodeId)

    def run(self):
        """Running task"""
        rOZW = None
        self._running = True
        if self._ozwManager._ozwLog :
            ozwfile = os.path.join(self._ozwManager._userPath + "OZW_Log.txt")
            if not os.path.isfile(ozwfile) :
                self._pluginLog.info(u"No existing openzwave log file : '{0}'. Monitor Nodes don't monitor openzwave lib.".format(ozwfile))
            else :
                try:
                    rOZW = MonitorOZW(self.logOZW_report, ozwfile, self._stop, self._pluginLog)
                    rOZW.start()
                except :
                    self._pluginLog.warning(u"MonitorOZW init error: {0}".format(traceback.format_exc()))
        else : self._pluginLog.info(u"No log activate for openzwave. Monitor Nodes don't monitor openzwave lib.")
        self._pluginLog.info(u'Monitor node(s) manager is started.')
        while not self._stop.isSet() and self._running :
            if self.__reports :
                report = self.__reports.popleft()
                idNetwork = 0
                if 'homeId' in report : idNetwork = report['homeId']
                elif 'networkId' in report : idNetwork = report['networkId']
                try :
                    self.logNode(report['date'], report['type'], idNetwork, report['nodeId'], report['datas'])
                except :
                    self._pluginLog.warning(u"Monitor node bad report : {0}, {1}".format(traceback.format_exc(), report))
            else : self._stop.wait(0.01)
        # flush and close list nodes
        for node in self.nodesMonitor :
            self.nodesMonitor[node].close()
            del self.nodesMonitor[node]
        if rOZW is not None : rOZW.stop()
        self._pluginLog.info(u'Monitor node(s) manager is stopped.')

    def stop(self):
        """Stop all thread of monitoring"""
        self._running = False

    def openzwave_report(self, args):
        """Callback from python-openzwave librairy
        """
        if self.isMonitored(args['homeId'], args['nodeId']) :
            self.__reports.append({'date': datetime.now(),'type': "Openzwave Notification : " + args['notificationType'], 'homeId': args['homeId'], 'nodeId': args['nodeId'], 'datas': args})

    def mq_report(self, device, dmgId):
        """Callback from MQ message"""
        if self.hasMonitored :
            if device is not None :
                homeId = self._ozwManager.getHomeID(device['networkid'])
                if 'node' in device :
                    if self.isMonitored(homeId, device['node']) :
                        if 'instance' in device :
                            self.__reports.append({'date': datetime.now(),'type': "MQ report : ",
                                    'homeId': homeId,
                                    'nodeId': device['node'],
                                    'instance': device['instance'],
                                    'datas' : str(dmgId)})
                        else:
                            self.__reports.append({'date': datetime.now(),'type': "MQ report : ",
                                    'homeId': homeId,
                                    'nodeId': device['node'],
                                    'datas' : str(dmgId)})
            else :
                self._pluginLog.warning(u"Can't do MQ report, domogik device controler of networkId unknown : {0} ".format(device))

    def nodeChange_report(self, homeId, nodeId, msg):
        """Callback from node himself."""
        if self.hasMonitored :
            if self.isMonitored(homeId, nodeId) :
                if msg.has_key('header') : del msg['header']
                if msg.has_key('node') : del msg['node']
                if msg.has_key('ctrldevice') : del msg['ctrldevice']
                self.__reports.append({'date': datetime.now(),'type': "Node change report : ", 'homeId': homeId, 'nodeId': nodeId, 'datas': msg})

    def nodeCompletMsg_report(self, homeId, nodeId, msg):
        """Callback from node himself."""
        if self.hasMonitored :
            if self.isMonitored(homeId, nodeId) :
                if msg.has_key('header') : del msg['header']
                if msg.has_key('node') : del msg['node']
                if msg.has_key('ctrldevice') : del msg['ctrldevice']
                self.__reports.append({'date': datetime.now(),'type': "Node receive completed message : ", 'homeId': homeId, 'nodeId': nodeId, 'datas': msg})

    def logOZW_report(self, line):
        """Callback from watch of openzwave log"""
        if self.hasMonitored :
            idx = line.find('Node')
            if  idx != -1 :
                try :
                    nodeId = int(line[idx+4:idx+7])
                    # TODO: Necessary loop due to openzwave log not send homeID, so all nodeId of all controllers are logged. To be updated when lib OK.
                    homeId = 0
                    for refNode, file in self.nodesMonitor.iteritems():
                        node = refNode.split('.')
                        if int(node[1]) == nodeId :
                            homeId = node[0]
                            break
                    if self.isMonitored(homeId,  nodeId) :
                        self.__reports.append({'date': datetime.now(),'type': "openzwave lib", 'homeId': homeId, 'nodeId': nodeId, 'datas': line})
                except :
                    pass

    def isMonitored(self, homeId, nodeId):
        """Return True if watch node."""
        if self.refNode(homeId, nodeId) in self.nodesMonitor:
            return True
        else:
            return False

    def getFileName(self, homeId, nodeId):
        """Return expected log name file."""
        node = self._ozwManager.getNetworkID(homeId)  + '_%03d' % nodeId
        return self._ozwManager._userPath + node +".log"

    def startMonitorNode(self, homeId, nodeId):
        """Start node watch in log file."""
        retval = {'error': ''}
        node = self._ozwManager._getNode(homeId, nodeId)
        if node is not None :
            fName = self.getFileName(homeId, nodeId)
            if not self.isMonitored(homeId, nodeId) :
                fLog = open(fName,  "w")
                self._pluginLog.info(u'Start monitor node {0} in log file : {1}.'.format(nodeId,  fName))
                retval.update({'state': 'started','usermsg':'Start monitor node {0} in log file.'.format(nodeId), 'file': fName})
                fLog.write("{0} - Started monitor log for node {1}.\n".format(datetime.now(),  nodeId))
                infos = node.getInfos()
                fLog.write("Node is registered in manager, state information : \n ")
                pprint.pprint(infos, stream=fLog)
                infos = node.getValuesInfos()
                pprint.pprint(infos, stream=fLog)
                fLog.write("===============================================\n")
                fLog.close()
                fLog = open(fName,  "a")  # reopen in append mode
                self.nodesMonitor.update({self.refNode(homeId, nodeId) : fLog})
            else :
                retval.update({'state': 'started','usermsg': 'Monitor node {0} in log already started.'.format(nodeId), 'file': fName})
                self._pluginLog.debug(u'Monitor node {0} in log already started.'.format(nodeId))
        else :
            retval['error'] = u"Can't start Monitor, Node is registered in manager (homeid: {0}, nodeId: {0})".format(homeId,  nodeId)
        return retval

    def stopMonitorNode(self, homeId, nodeId):
        """Stop watch for node"""
        retval = {'error': ''}
        node = self._ozwManager._getNode(homeId, nodeId)
        if node is not None :
            if self.isMonitored(homeId, nodeId) :
                fLog = self.nodesMonitor[self.refNode(homeId, nodeId)]
                retval.update({'state': 'stopped','usermsg': 'Stop monitor node {0} in log file.'.format(nodeId), 'file': self.getFileName(homeId, nodeId)})
                self._pluginLog.info(u'Stop monitor node {0} in log file : {1}.'.format(nodeId,  self.getFileName(homeId, nodeId)))
                fLog.write("{0} - Stopped monitor log for node {1}.".format(datetime.now(),  nodeId))
                fLog.close()
                del self.nodesMonitor[self.refNode(homeId, nodeId)]
            else :
                retval.update({'error': 'Monitor node {0}.{1} not running.'.format(homeId, nodeId)})
        else :
            retval['error'] = u"Can't stop Monitor, Node is registered in manager (homeid: {0}, nodeId: {0})".format(homeId,  nodeId)
        return retval
        return retval

    def logNode(self, date,  type, homeId, nodeId, args):
        """log node informations in file NetworkID_NodeID.log, stored in data/ozwave"""
        fLog = self.nodesMonitor[self.refNode(homeId, nodeId)]
        if type == 'openzwave lib':
            fLog.write('{0}\n'.format(args))
        else :
            fLog.write("{0} - {1}\n".format(date,  type))
            if isinstance(args,  str) :
                fLog.write(args + "\n")
            else :
                pprint.pprint(args, stream=fLog)
            fLog.write("-----------------------------------------------------------\n")

class MonitorOZW(threading.Thread):
    """Class for monitor openzwave log"""

    def __init__(self, cb_logNode, ozwlogfile, stop, pluginLog):
        """Create watch instance for openzwave log"""
        threading.Thread.__init__(self)
        self.name = "Manage_Monitor_Log Openzwave"
        self.cb_logNode = cb_logNode
        self.ozwlogfile = ozwlogfile
        self._stop = stop
        self._pluginLog = pluginLog
        self._pluginLog.info(u'Monitor openzwave manager is initialized.')
        self.running = False

    def run(self):
        """Start thread of watching openzwave log."""
        self._pluginLog.info(u'Monitor openzwave manager is started.')
        self.running = True
        ozwTail = Tailer(open(self.ozwlogfile, 'rb'))
        for line in ozwTail.follow(delay=0.01):
            if line : self.cb_logNode(line)
            if self._stop.isSet() or not self.running : break
        self.running = False
        self._pluginLog.info(u'Monitor openzwave manager is stopped.')

    def stop(self):
        """Stop thread of watching openzwave log at next log."""
        self.running = False
