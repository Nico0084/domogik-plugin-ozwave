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
@copyright: (C) 2007-2016 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

#import libopenzwave
#from libopenzwave import PyManager
from collections import namedtuple


FlagDebug = False # pour debug eviter recurtion +2, passé a True pour debug

# Déclaration de tuple nomée pour la clarification des infos des noeuds zwave (node)
# Juste à rajouter ici la déclaration pour future extension.
NamedPair = namedtuple('NamedPair', ['id', 'name'])
NodeInfo = namedtuple('NodeInfo', ['generic', 'basic', 'specific', 'security', 'version'])

# Status des membres d'un group d'association pour gestion des mises à jour des nodes sleeping
MemberGrpStatus = {  0: 'unknown',
                     1: 'confirmed',
                     2: 'to confirm',
                     3: 'to update'}
# Status des nodes dans le reseau zwave
NodeStatusNW = {  0:'Uninitialized',
                  1:'Initialized - not known',
                  2:'Completed',
                  3:'In progress - Devices initializing',
                  4:'In progress - Linked to controller',
                  5:'In progress - Can receive messages',
                  6:'Out of operation',
                  7:'In progress - Can receive messages (Not linked)'}

Capabilities = ['Primary Controller', 'Secondary Controller', 'Static Update Controller', 'Bridge Controller' ,
                'Routing', 'Listening', 'Beaming', 'Security', 'FLiRS']

# Listes de commandes Class reconnues comme device domogik , il semble que la COMMAND_CLASS_BASIC ne soit pas util pour la device domogik.
CmdsClassAvailable = [ 'COMMAND_CLASS_SWITCH_BINARY', 'COMMAND_CLASS_SENSOR_BINARY',
                       'COMMAND_CLASS_SENSOR_MULTILEVEL', 'COMMAND_CLASS_BATTERY', 'COMMAND_CLASS_METER',
                       'COMMAND_CLASS_SWITCH_MULTILEVEL', 'COMMAND_CLASS_THERMOSTAT_SETPOINT', 'COMMAND_CLASS_ALARM',
                       'COMMAND_CLASS_SENSOR_ALARM', 'COMMAND_CLASS_THERMOSTAT_FAN_MODE', 'COMMAND_CLASS_THERMOSTAT_FAN_STATE',
                       'COMMAND_CLASS_THERMOSTAT_MODE', 'COMMAND_CLASS_THERMOSTAT_HEATING', 'COMMAND_CLASS_THERMOSTAT_OPERATING_STATE']

# List off all recognized Label as device domogik (label openzwave) - List loaded directly from json sensors and commands
DomogikLabelAvailable = []

# Notifications reported to MQ for Admin
UICtrlReportType = ['plugin-state', 'driver-ready', 'driver-remove', 'init-process', 'ctrl-error', 'ctrl-action',
                            'node-state-changed', 'value-changed', 'polling']

# Listes de commandes Class pour conversion des notifications NodeEvent en ValueChanged
CmdsClassBasicType = ['COMMAND_CLASS_SWITCH_BINARY', 'COMMAND_CLASS_SENSOR_BINARY', 'COMMAND_CLASS_SENSOR_MULTILEVEL',
                      'COMMAND_CLASS_SWITCH_MULTILEVEL',  'COMMAND_CLASS_SWITCH_ALL',  'COMMAND_CLASS_SWITCH_TOGGLE_BINARY',
                      'COMMAND_CLASS_SWITCH_TOGGLE_MULTILEVEL', 'COMMAND_CLASS_SENSOR_MULTILEVEL','COMMAND_CLASS_METER',
                      'COMMAND_CLASS_THERMOSTAT_SETPOINT', 'COMMAND_CLASS_SENSOR_ALARM']

class OZwaveException(Exception):
    """"Zwave generic exception class.
    """
    def __init__(self, value):
        """Initialisation"""
        Exception.__init__(self, value)
        self.msg = "OZwave generic exception:"
        self.value = value

    def __str__(self):
        """String format object"""
        return repr(self.msg+' '+self.value)


