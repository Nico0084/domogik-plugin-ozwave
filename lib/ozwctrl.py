# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}$

License
=======

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
==============

Support Z-wave technology

Implements
==========

-Zwave

@author: Nico <nico84dev@gmail.com>
@author: bibi21000 aka Sébastien GALLET <bibi21000@gmail.com>
@copyright: (C) 2007-2012 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

import libopenzwave
from ozwnode import ZWaveNode
from ozwdefs import *
import time

class OZwaveCtrlException(OZwaveException):
    """"Zwave Controller exception  class"""

    def __init__(self, value):
        OZwaveException.__init__(self, value)
        self.msg = "OZwave Controller exception:"

class ZWaveController(ZWaveNode):
    '''
    The controller manager.

    Allows to retrieve informations about the library, statistics, ...
    Also used to send commands to the controller

Commands :

- Driver::ControllerCommand_AddDevice - Add a new device or controller to the Z-Wave network.
- Driver::ControllerCommand_CreateNewPrimary - Create a new primary controller when old primary fails. Requires SUC.
- Driver::ControllerCommand_ReceiveConfiguration - Receive network configuration information from primary controller. Requires secondary.
- Driver::ControllerCommand_RemoveDevice - Remove a device or controller from the Z-Wave network.
- Driver::ControllerCommand_RemoveFailedNode - Remove a node from the network. The node must not be responding and be on the controller's failed node list.
- Driver::ControllerCommand_HasNodeFailed - Check whether a node is in the controller's failed nodes list.
- Driver::ControllerCommand_ReplaceFailedNode - Replace a failed device with another. If the node is not in
            the controller's failed nodes list, or the node responds, this command will fail.
- Driver:: ControllerCommand_TransferPrimaryRole - Add a new controller to the network and
            make it the primary. The existing primary will become a secondary controller.
- Driver::ControllerCommand_RequestNetworkUpdate - Update the controller with network information from the SUC/SIS.
- Driver::ControllerCommand_RequestNodeNeighborUpdate - Get a node to rebuild its neighbour list. This method also does RequestNodeNeighbors afterwards.
- Driver::ControllerCommand_AssignReturnRoute - Assign a network return route to a device.
- Driver::ControllerCommand_DeleteAllReturnRoutes - Delete all network return routes from a device.
- Driver::ControllerCommand_SendNodeInformation - Send a node information frame.
- Driver::ControllerCommand_ReplicationSend - Send information from primary to secondary
- Driver::ControllerCommand_CreateButton - Create a handheld button id.
- Driver::ControllerCommand_DeleteButton - Delete a handheld button id.

Callbacks :

- Driver::ControllerState_Waiting, the controller is waiting for a user action. A notice should be displayed
        to the user at this point, telling them what to do next.
        For the add, remove, replace and transfer primary role commands, the user needs to be told to press the
        inclusion button on the device that is going to be added or removed. For ControllerCommand_ReceiveConfiguration,
        they must set their other controller to send its data, and for ControllerCommand_CreateNewPrimary, set the other
        controller to learn new data.
- Driver::ControllerState_InProgress - the controller is in the process of adding or removing the chosen node. It is now too late to cancel the command.
- Driver::ControllerState_Complete - the controller has finished adding or removing the node, and the command is complete.
- Driver::ControllerState_Failed - will be sent if the command fails for any reason.

    '''

    def __init__(self,  ozwmanager, homeId, nodeId,  isPrimaryCtrl=False,  networkId =""):
        '''
        Innitialise un controlleur.

        @param ozwmanager: pointeur sur l'instance du manager
        @param homeid: ID du réseaux home/controleur
        @param nodeid: ID du node
        @param isPrimaryCtrl: Identifie si le controlleur est le primaire d'un réseaux
        @param networkId: Nom optionel d'un controleur primaire, est utile pour remplacer le Home ID dans les message xPL
        '''
        if nodeId is None:
            nodeId = 1
        ZWaveNode.__init__(self, ozwmanager, homeId, nodeId)
        self._isPrimaryCtrl = isPrimaryCtrl
        self.networkId = networkId if self._isPrimaryCtrl else ""
        self._lastCtrlState = {'update' : time.time(),
                                  'state': libopenzwave.PyControllerState[0],
                                  'stateMsg': libopenzwave.PyControllerState[0].doc,
                                  'stateId': 0,
                                  'error' : libopenzwave.PyControllerError[0],
                                  'errorMsg' : libopenzwave.PyControllerError[0].doc,
                                  'errorId' : 0,
                                  'nodeId': 0,
                                  'command': libopenzwave.PyControllerCommand[0]
                                  }

# On accède aux attributs uniquement depuis les property
    isPrimaryCtrl = property(lambda self: self._isPrimaryCtrl)
    getNetworkCtrl = property(lambda self: self._ozwmanager.getCtrlOfNetwork(self._homeId))

    def __str__(self):
        """
        The string representation of the node.
        :rtype: str
        """
        typeCtrl = "the primary" if self.isPrimaryCtrl else "a secondary"
        return 'homeId: [{0}]  nodeId: [{1}] product: {2}  name: {3} is it {4} controller'.format(self._homeId, self._nodeId, self._product, self._name, typeCtrl)

    def getLastState(self):
        """Retourne le dernier etat connus du zwctrl controlleur et issue du callback des messages action"""
        return self._lastCtrlState

    def reportChangeToUI(self, report):
        """Envois un report de changement/notification du réseau zwave en générant un evénement
            à destination de l'UI a travers la MQ.
        """
        msg = report.copy()
        msg["NetworkID"] = self.networkID
        msg["Node count"] = self.getNetworkCtrl.getNodeCount()
        msg["Node sleeping"] = self.getNetworkCtrl.getSleepingNodeCount()
        msg["Node fail"] = self.getNetworkCtrl.getFailedNodeCount()
        print 'Send report to MQ: '
        self._ozwmanager._plugin.publishMsg('ozwave.ctrl.report', msg)
        print '**************************************'

    def stats(self):
        """
        Retrieve statistics from driver.

        Statistics:

            * s_SOFCnt                         : Number of SOF bytes received
            * s_ACKWaiting                     : Number of unsolicited messages while waiting for an ACK
            * s_readAborts                     : Number of times read were aborted due to timeouts
            * s_badChecksum                    : Number of bad checksums
            * s_readCnt                        : Number of messages successfully read
            * s_writeCnt                       : Number of messages successfully sent
            * s_CANCnt                         : Number of CAN bytes received
            * s_NAKCnt                         : Number of NAK bytes received
            * s_ACKCnt                         : Number of ACK bytes received
            * s_OOFCnt                         : Number of bytes out of framing
            * s_dropped                        : Number of messages dropped & not delivered
            * s_retries                        : Number of messages retransmitted
            * s_controllerReadCnt              : Number of controller messages read
            * s_controllerWriteCnt             : Number of controller messages sent

        :return: Statistics of the controller
        :rtype: dict()

        """
        return self._manager.getDriverStatistics(self.homeId)

    def _updateCapabilities(self):
        """
        Surchage de la méthode hérité de ZWaveNode : Mise à jour des capabilities set du node
        Capabilities = ['Primary Controller', 'Secondary Controller', 'Static Update Controller','Bridge Controller' ,'Routing', 'Listening', 'Beaming', 'Security', 'FLiRS']
        """
        nodecaps = set()
        if self._manager.isNodeRoutingDevice(self._homeId, self._nodeId): nodecaps.add('Routing')
        if self._manager.isNodeListeningDevice(self._homeId, self._nodeId): nodecaps.add('Listening')
        if self._manager.isNodeBeamingDevice(self._homeId, self._nodeId): nodecaps.add('Beaming')
        if self._manager.isNodeSecurityDevice(self._homeId, self._nodeId): nodecaps.add('Security')
        if self._manager.isNodeFrequentListeningDevice(self._homeId, self._nodeId): nodecaps.add('FLiRS')
        if self.isPrimaryCtrl:
            nodecaps.add('Primary Controller')
            if self._manager.isStaticUpdateController(self._homeId): nodecaps.add('Static Update Controller')
            if self._manager.isBridgeController(self._homeId): nodecaps.add('Bridge Controller')
        else : nodecaps.add('Secondary Controller')
        self._capabilities = nodecaps
        self._ozwmanager._log.debug('Node [%d] capabilities are: %s', self._nodeId, self._capabilities)

    def handle_Action(self,  action):
        """Handle request controlleur action from MQ"""
        retval = action
        retval['error'] = ''
        if action['action'] =='getState':
            retval.update({'state': self._lastCtrlState['state'],
                                 'usermsg' : self._lastCtrlState['stateMsg'],
                                 'error' : '' if self._lastCtrlState['errorId'] == 0 else self._lastCtrlState['errorMsg'],
                                 'command' : 'Internal' if self._lastCtrlState['command'] == 'None' else self._lastCtrlState['command'],
                                 'nodeId': self._lastCtrlState['nodeId']
                                })
            return retval
        errorCom = {'error': 'Not started, check your controller.'}
        errorNode ={'error': 'Unknown node : {0}, check input options.'.format(action['nodeid'])}
        if action['dosecurity'] =='True' : doSecurity = True
        else : doSecurity = False
        if action['action'] == 'stop' :
            if self.cancel_command() :
                retval['error'] = ''
                retval['message'] = 'User have stop command.'
            else :
                retval['error'] = 'Fail to stop controller commande.'
                if self._lastCtrlState['state'] == libopenzwave.PyControllerState[0] :
                    retval['message'] = 'User have try stop command. But no action processing.'
                else :
                    retval['message'] = 'User have try stop command. ' + self._lastCtrlState['command']
        elif action['action'] == 'start' :
            retval['message'] ='Command will be root soon as possible, be patient....'
            self._lastCtrlState['command'] = action['command']
            self._lastCtrlState['nodeId'] = action['nodeid']
            if action['command'] == 'AddDevice' :
                if self.add_node(doSecurity) :
                    retval['message'] ='It is up to you to perform the action on the local device(s) to add. Usually a switch to actuate 2 or 3 times.'
                else : retval.update(errorCom)

            elif action['command'] == 'CreateNewPrimary' :
                if self.create_new_primary() :
                    retval['message'] ='Wait for refresh, be patient...'
                else : retval.update(errorCom)

            elif action['action'] == 'ReceiveConfiguration' :
                if self.receive_configuration() :
                    retval['message'] ='Wait for refresh, be patient...'
                else : retval.update(errorCom)

            elif action['command'] == 'RemoveDevice' :
                if self.remove_node() :
                    retval['message'] ='It is up to you to perform the action on the local device(s) to renove. Usually a switch to actuate 2 or 3 times.'
                else : retval.update(errorCom)

            elif action['command'] =='RemoveFailedNode':
                if action['nodeid'] is None or action['nodeid'] == 0 :
                    self._ozwmanager._log.error('No action.nodeid for controleur command, quit')
                    node = None
                else :
                    node = self._ozwmanager._getNode(self.homeId, action['nodeid'])
                if node :
                    if self.remove_failed_node(action['nodeid']) :
                        retval['message'] ='Wait for removing node, be patient...'
                    else : retval.update(errorCom)
                else : retval.update(errorNode)

            elif action['command'] =='HasNodeFailed':
                if action['nodeid'] is None or action['nodeid'] == 0 :
                    self._ozwmanager._log.error('No action.nodeid for controleur command, quit')
                    print ('ERROR : No action.nodeid for controleur command, quit')
                    node = None
                else :
                    node = self._ozwmanager._getNode(self.homeId, action['nodeid'])
                if node :
                    if self.has_node_failed(action['nodeid']) :
                        retval['message'] ='Wait for research, be patient...'
                    else : retval.update(errorCom)
                else : retval.update(errorNode)

            elif action['command'] =='ReplaceFailedNode':
                if  action['nodeid'] is None or action['nodeid'] == 0 :
                    self._ozwmanager._log.error('No action.nodeid for controleur command, quit')
                    print ('ERROR : No action.nodeid for controleur command, quit')
                    node = None
                else :
                    node = self._ozwmanager._getNode(self.homeId, action['nodeid'])
                if node :
                    if self.replace_failed_node(action['nodeid']) :
                        retval['message'] ='Wait for replace node failed, be patient...'
                    else : retval.update(errorCom)
                else : retval.update(errorNode)

            elif action['command'] == 'TransferPrimaryRole' :
                if self.transfer_primary_role() :
                    retval['message'] = 'Add a new controller to the network and make it the primary. The existing primary will become a secondary controller.'
                else : retval.update(errorCom)

            elif action['command'] == 'RequestNetworkUpdate' :
                if  action['nodeid'] is not None and action['nodeid'] != 0 :
                    if self.request_network_update(action['nodeid']) :
                        retval['message'] ='Wait for refresh, be patient...'
                    else : retval.update(errorCom)
                else : retval.update(errorNode)

            elif action['command'] =='RequestNodeNeighborUpdate':
                if  action['nodeid'] is None or action['nodeid'] == 0 :
                    self._ozwmanager._log.error('No action.nodeid for controleur command, quit')
                    print ('ERROR : No action.nodeid for controleur command, quit')
                    node = None
                else :
                    node = self._ozwmanager._getNode(self.homeId, action['nodeid'])
                if node :
                    if self.request_Node_Neighbor_Update(action['nodeid']) :
                        retval['message'] ='Wait for refresh, be patient...'
                    else : retval.update(errorCom)
                else : retval.update(errorNode)

            elif action['command'] =='AssignReturnRoute':
                if  action['nodeid'] is None or action['nodeid'] == 0 :
                    self._ozwmanager._log.error('No action.nodeid for controleur command, quit')
                    print ('ERROR : No action.nodeid for controleur command, quit')
                    node = None
                else :
                    node = self._ozwmanager._getNode(self.homeId, action['nodeid'])
                if node : # and nodeDest :
                    if self.assign_return_route(action['nodeid']) :
                        retval['message'] ='Wait for route assign, be patient...'
                    else : retval.update(errorCom)
                else : retval.update(errorNode)

            elif action['command'] =='DeleteAllReturnRoutes':
                if  action['nodeid'] is None or action['nodeid'] == 0 :
                    self._ozwmanager._log.error('No action.nodeid for controleur command, quit')
                    print ('ERROR : No action.nodeid for controleur command, quit')
                    node = None
                else :
                    node = self._ozwmanager._getNode(self.homeId, action['nodeid'])
                if node :
                    if self.delete_all_return_routes(action['nodeid']) :
                        retval['message'] ='Wait for deleting return route, be patient...'
                    else : retval.update(errorCom)
                else : retval.update(errorNode)

            elif action['command'] =='SendNodeInformation':
                if  action['nodeid'] is None or action['nodeid'] == 0 :
                    self._ozwmanager._log.error('No action.nodeid for controleur command, quit')
                    node = None
                else :
                    node = self._ozwmanager._getNode(self.homeId, action['nodeid'])
                if node :
                    if self.send_node_information(action['nodeid']) :
                        retval['message'] ='Wait get node information, be patient...'
                    else : retval.update(errorCom)
                else : retval.update(errorNode)

            elif action['command'] == 'ReplicationSend' :
                if  action['nodeid'] is not None and action['nodeid'] != 0 :
                    if self.replication_send(action['nodeid']) :
                        retval['message'] ='Wait for sending information from primary to secondary, be patient...'
                    else : retval.update(errorCom)
                else : retval.update(errorNode)
            if retval['error'] != '' :
                retval['message'] ='Command not sended.'
 # TODO: CreateButton , DeleteButton

        else :
            retval['error'] = 'Unknown action : ' + action['action']
            retval['message'] ='Command error'
            retval['state']  = 'Stop'
        return retval

    def _getValue(self, valueId):
        """Retourn l'objet Value correspondant au valueId"""
        retval= None
        for node in self._nodes.values():
            if node._values.has_key(valueId):
                retval = node._values[valueId]
                break
        return retval

    def hard_reset(self):
        """
        Hard Reset a PC Z-Wave Controller.
        Resets a controller and erases its network configuration settings.  The
        controller becomes a primary controller ready to add devices to a new network.
        """
        if self.isPrimaryCtrl :
            self._manager.resetController(self.homeId)
            print('************  Hard Reset du controlleur ***********')
            self._ozwmanager._log.debug('Hard Reset of ZWave controller')
            return True
        else:
            self._ozwmanager._log.debug('No Hard Reset on secondary controller')
            return False

    def soft_reset(self):
        """
        Soft Reset a PC Z-Wave Controller.
        Resets a controller without erasing its network configuration settings.
        """
        if self.isPrimaryCtrl :
            self._manager.softResetController(self.homeId)
            print('************  Soft Reset du controlleur ***********')
            self._ozwmanager._log.debug('Soft Reset of ZWave controller')
            return True
        else:
            self._ozwmanager._log.debug('No Soft Reset on secondary controller')
            return False

    def cmdsAvailables(self):
        """
        Return all availables crontroller commands with associate documentations
         :return: list of commands
         :rtype: dict
        """
        retval={}
        for elem in  libopenzwave.PyControllerCommand :
            if elem != 'None' : retval[elem] = str(elem.doc)
        return retval

    def add_node(self, doSecurity = False):
        """
        Start the Inclusion Process to add a Node to the Network.
        The Status of the Node Inclusion is communicated via Notifications. Specifically, you should
        monitor ControllerCommand Notifications.

        Results of the AddNode Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The Home ID of the Z-Wave network where the device should be added.
        :param _doSecurity: Whether to initialize the Network Key on the device if it supports the Security CC
        :return: True if the Command was sent succcesfully to the Controller
        """
        return self._manager.addNode(self.homeId, doSecurity)

    def remove_node(self):
        """
        Remove a Device from the Z-Wave Network
        The Status of the Node Removal is communicated via Notifications. Specifically, you should
        monitor ControllerCommand Notifications.

        Results of the AddNode Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network where you want to remove the device
        :return: True if the Command was send succesfully to the Controller
        """
        return self._manager.removeNode(self.homeId)

    def remove_failed_node(self, node_id):
        """
        Remove a Failed Device from the Z-Wave Network
        This Command will remove a failed node from the network. The Node should be on the Controllers Failed
        Node List, otherwise this command will fail. You can use the HasNodeFailed function below to test if the Controller
        believes the Node has Failed.
        The Status of the Node Removal is communicated via Notifications. Specifically, you should
        monitor ControllerCommand Notifications.

        Results of the AddNode Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network where you want to remove the device
        :param _nodeId: The NodeID of the Failed Node.
        :return: True if the Command was send succesfully to the Controller
        """
        return self._manager.removeFailedNode(self.homeId, node_id)

    def has_node_failed(self, node_id):
        """
        Check if the Controller Believes a Node has Failed.
        This is different from the IsNodeFailed call in that we test the Controllers Failed Node List, whereas the IsNodeFailed is testing
        our list of Failed Nodes, which might be different.
        The Results will be communicated via Notifications. Specifically, you should monitor the ControllerCommand notifications

        Results of the AddNode Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network where you want to test the device
        :param _nodeId: The NodeID of the Failed Node.
        :return: True if the RemoveDevice Command was send succesfully to the Controller
        """
        return self._manager.hasNodeFailed(self.homeId, node_id)

    def request_Node_Neighbor_Update(self, node_id):
        """
        Ask a Node to update its Neighbor Tables
        This command will ask a Node to update its Neighbor Tables.

        Results of the AddNode Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network where you want to update the device
        :param _nodeId: The NodeID of the Node.
        :return: True if the Command was send succesfully to the Controller
        """
        return self._manager.requestNodeNeighborUpdate(self.homeId, node_id)

    def assign_return_route(self, node_id):
        """
        Ask a Node to update its update its Return Route to the Controller
        This command will ask a Node to update its Return Route to the Controller

        Results of the AddNode Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId:The HomeID of the Z-Wave network where you want to update the device
        :param _nodeId: The NodeID of the Node.
        :return: True if the Command was send succesfully to the Controller
        """
        return self._manager.assignReturnRoute(self.homeId, node_id)

    def delete_all_return_routes(self, node_id):
        """
        Ask a Node to delete all Return Route.
        This command will ask a Node to delete all its return routes, and will rediscover when needed.

        Results of the AddNode Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network where you want to update the device
        :param _nodeId: The NodeID of the Node.
        :return: True if the Command was send succesfully to the Controller
        """
        return self._manager.deleteAllReturnRoutes(self.homeId, node_id)

    def send_node_information(self, node_id):
        """
        Send a NIF frame from the Controller to a Node.
        This command send a NIF frame from the Controller to a Node

        Results of the AddNode Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network
        :param _nodeId: The NodeID of the Node to recieve the NIF
        :return: True if the sendNIF Command was send succesfully to the Controller
        """
        return self._manager.sendNodeInformation(self.homeId, node_id)

    def create_new_primary(self):
        """
        Create a new primary controller when old primary fails. Requires SUC.
        This command Creates a new Primary Controller when the Old Primary has Failed. Requires a SUC on the network to function

        Results of the CreateNewPrimary Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network
        :return: True if the CreateNewPrimary Command was send succesfully to the Controller
        """
        return self._manager.createNewPrimary(self.homeId)

    def receive_configuration(self):
        """
        Receive network configuration information from primary controller. Requires secondary.
        This command prepares the controller to recieve Network Configuration from a Secondary Controller.

        Results of the ReceiveConfiguration Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network
        :return: True if the ReceiveConfiguration Command was send succesfully to the Controller
        """
        return self._manager.receiveConfiguration(self.homeId)

    def replace_failed_node(self, node_id):
        """
        Replace a failed device with another.
        If the node is not in the controller's failed nodes list, or the node responds, this command will fail.
        You can check if a Node is in the Controllers Failed node list by using the HasNodeFailed method

        Results of the ReplaceFailedNode Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network
        :param _nodeId: the ID of the Failed Node
        :return: True if the ReplaceFailedNode Command was send succesfully to the Controller
        """
        return self._manager.replaceFailedNode(self.homeId, node_id)

    def transfer_primary_role(self):
        """
        Add a new controller to the network and make it the primary.
        The existing primary will become a secondary controller.

        Results of the TransferPrimaryRole Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network
        \return: True if the TransferPrimaryRole Command was send succesfully to the Controller
        """
        return self._manager.transferPrimaryRole(self.homeId)

    def request_network_update(self, node_id):
        """
        Update the controller with network information from the SUC/SIS.

        Results of the RequestNetworkUpdate Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network
        :param _nodeId: the ID of the Node
        :return: True if the RequestNetworkUpdate Command was send succesfully to the Controller
        """
        return self._manager.requestNetworkUpdate(self.homeId, node_id)

    def replication_send(self, node_id):
        """
        Send information from primary to secondary

        Results of the ReplicationSend Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network
        :param _nodeId: the ID of the Node
        :\return: True if the ReplicationSend Command was send succesfully to the Controller
        """
        return self._manager.replicationSend(self.homeId, node_id)

    def create_button(self, node_id, arg=0):
        """
        Create a handheld button id.

        Only intended for Bridge Firmware Controllers.

        Results of the CreateButton Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network
        :param _nodeId: the ID of the Virtual Node
        :param _buttonId: the ID of the Button to create
        :return: True if the CreateButton Command was send succesfully to the Controller
        """
        return self._manager.createButton(self.homeId, node_id, arg)

    def delete_button(self, node_id, arg=0):
        """
        Delete a handheld button id.

        Only intended for Bridge Firmware Controllers.

        Results of the DeleteButton Command will be send as a Notification with the Notification type as
        Notification::Type_ControllerCommand

        :param _homeId: The HomeID of the Z-Wave network
        :param _nodeId: the ID of the Virtual Node
        :param _buttonId: the ID of the Button to delete
        :return: True if the DeleteButton Command was send succesfully to the Controller
        """
        return self._manager.deleteButton(self.homeId, node_id, arg)

    def cancel_command(self):
        """
        Cancels any in-progress command running on a controller.
        :param _homeId: The Home ID of the Z-Wave controller.
        :return: True if a command was running and was cancelled.
        """
        self._ozwmanager._log.debug('Try to cancel controller {0} command : {1}'.format(self._ozwmanager.getHomeID(self.homeId), self._lastCtrlState))
        return self._manager.cancelControllerCommand(self.homeId)

    def checkActionCtrl(self):
        """
        Check if controller action is in state finished return None is not finish or all state if finished
        None for : ['Normal', 'Cancel', 'Error', 'Completed', 'Failed' 'NodeOK', 'NodeFailed']
        State for :[''Starting', 'Waiting', 'Sleeping', 'InProgress']
        """
        if self._lastCtrlState['state'] not in [libopenzwave.PyControllerState[1], libopenzwave.PyControllerState[4],
                                                            libopenzwave.PyControllerState[5], libopenzwave.PyControllerState[6]] :
            return self._lastCtrlState
        else : return None

    def handleNotificationCommand(self, args):
        """Handle notification ControllerCommand from openzwave."""
        if args['controllerState'] == libopenzwave.PyControllerState[0] :
            self._lastCtrlState['nodeId'] = args['nodeId']
            self._lastCtrlState['command'] = libopenzwave.PyControllerCommand[0]
        if args['nodeId'] != 0 :
            self._lastCtrlState['nodeId'] = args['nodeId']
        self._lastCtrlState.update({ 'update' : time.time(),
                                              'state': args['controllerState'],
                                              'stateMsg': args['controllerStateDoc'],
                                              'stateId': args['controllerStateInt'],
                                              'error' : args['controllerError'],
                                              'errorMsg' : args['controllerErrorDoc'],
                                              'errorId' : args['controllerErrorInt']
                                              })
        self.publishCommandState()

    def publishCommandState(self):
        """Publish a controller command state over MQ"""
        self._ozwmanager._plugin.publishMsg('ozwave.ctrl.command', {'NetworkID': self.networkID,
                'state': self._lastCtrlState['state'],
                'usermsg' : self._lastCtrlState['stateMsg'],
                'error' : '' if self._lastCtrlState['errorId'] == 0 else self._lastCtrlState['errorMsg'],
                'command' : 'Internal' if self._lastCtrlState['command'] == 'None' else self._lastCtrlState['command'],
                'nodeId': self._lastCtrlState['nodeId']
                })

#@DEPRECIATE
#TODO: delete after all begin_command_* modifed to direct command
#    def zwcallback(self, args):
#        """
#        The Callback Handler used when sendig commands to the controller.
#
#        To do : add node in signal when necessary
#
#        :param args: A dict containing informations about the state of the controller
#        :type args: dict()
#
#        """
#        self._ozwmanager._log.debug('Controller state change : %s' % (args))
#        if self._lastCtrlState.has_key ('nodeid') : args['nodeid'] = self._lastCtrlState['nodeid']
#        self._lastCtrlState = args
#        self._lastCtrlState["update"]= time.time()
#        state = args['state']
#        message = args['message']
#        print 'zwcallback Action State :', state, ' -- message :', message, ' -- controller', self
#        self._ozwmanager.reportCtrlMsg(self.homeId,  self._lastCtrlState)
#
# -----------------------------------------------------------------------------
# Polling Z-Wave devices
# -----------------------------------------------------------------------------
# Methods for controlling the polling of Z-Wave devices.  Modern devices will
# not require polling.  Some old devices need to be polled as the only way to
# detect status changes.
#
    def getPollInterval(self):
        """Get the time period between polls of a nodes state

            :return: The number of milliseconds between polls
            :rtype: int"""
        return self._manager.getPollInterval()

    def setPollInterval(self, milliseconds, bIntervalBetweenPolls = False ):
        """Set the time period between polls of a nodes state.
            Due to patent concerns, some devices do not report state changes automatically
            to the controller.  These devices need to have their state polled at regular
            intervals.  The length of the interval is the same for all devices.  To even
            out the Z-Wave network traffic generated by polling, OpenZWave divides the
            polling interval by the number of devices that have polling enabled, and polls
            each in turn.  It is recommended that if possible, the interval should not be
            set shorter than the number of polled devices in seconds (so that the network
            does not have to cope with more than one poll per second).

            :param milliseconds: The length of the polling interval in milliseconds.
            :type milliseconds: int
            :param bIntervalBetweenPolls: If True, the library intersperses m_pollInterval between polls.
                                                           If False, the library attempts to complete all polls within m_pollInterval
            :type bIntervalBetweenPolls: bool"""
        self._manager.setPollInterval(milliseconds, bIntervalBetweenPolls)
        self.pollInterval = milliseconds

    def enablePoll(self, nodeId,  valueId,  intensity = 1):
        node = self._ozwmanager._getNode(self.homeId,  nodeId)
        value = node.getValue(valueId)
        if value :
            retval = value.enablePoll(intensity)
            if retval == True :
                return {'error': ""}
            else: {'error' : "Fail enable poll node {0}, value {1}, with intensity : {3}, {4}".format(nodeId,  valueId, intensity,  retval['error'])}
        else : return {'error' : "Unknown value %d" % valueId}

    def disablePoll(self, nodeId,  valueId):
        node = self._ozwmanager._getNode(self.homeId,  nodeId)
        value = node.getValue(valueId)
        if value :
            if value.disablePoll() :
                return {'error': ""}
            else: {'error' : "Fail disable poll %d" % valueId}
        else : return {'error' : "Unknown value %d" % valueId}
