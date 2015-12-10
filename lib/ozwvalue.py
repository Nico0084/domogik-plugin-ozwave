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

from ozwdefs import *
import time
import sys

class OZwaveValueException(OZwaveException):
    """"Zwave ValueNode exception class"""

    def __init__(self, value):
        OZwaveException.__init__(self, value)
        self.msg = "OZwave Value exception:"


class ZWaveValueNode:
    """ Représente une des valeurs du node """
    def __init__(self, node, valueData):
        '''
        Initialise la valeur du node
        @param node: ZWaveNode node 'parent'
        @param valueData: valueId dict (voir libopenzwave.pyx)
            ['valueId'] = {
                    'homeId' : uint32, # Id du réseaux
                    'nodeId' : uint8,   # Numéro du noeud
                    'commandClass' : PyManager.COMMAND_CLASS_DESC[v.GetCommandClassId()], # Liste des cmd CLASS reconnues
                    'instance' : uint8  # numéro d'instance de la value
                    'index' : uint8 # index de classement de la value
                    'id' : uint64 # Id pointeur C++ de la value
                    'genre' : enum ValueGenre:   # Type de data OZW
                                ValueGenre_Basic = 0
                                ValueGenre_User = 1
                                ValueGenre_Config = 2
                                ValueGenre_System = 3
                                ValueGenre_Count = 4
                    'type' : enum ValueType:  # Type de données
                                ValueType_Bool = 0
                                ValueType_Byte = 1
                                ValueType_Decimal = 2
                                ValueType_Int = 3
                                ValueType_List = 4
                                ValueType_Schedule = 5
                                ValueType_Short = 6
                                ValueType_String = 7
                                ValueType_Button = 8
                                ValueType_Max = ValueType_Button

                    'value' : str,      # Valeur même
                    'label' : str,      # Nom de la value OZW
                    'units' : str,      # unité
                    'readOnly': manager.IsValueReadOnly(v),  # Type d'accès lecture/ecriture
                    'min' :  uint   # the minimum that this value may contain.
                    'max' :  uint   # the maximum that this value may contain.
                    }
        '''
        self._node = node
        self._valueData = valueData
        self._lastUpdate = time.time()
        self._realValue = None
        self._tempConv = True # Conversion forcée de F en °C, a mettre en option.
        self._valueData['min'] = self._node._manager.getValueMin(self._valueData['id'])
        self._valueData['max'] = self._node._manager.getValueMax(self._valueData['id'])

    # On accède aux attributs uniquement depuis les property
    log = property(lambda self: self._node._ozwmanager._log)
    homeId = property(lambda self: self._node._homeId)
    nodeId = property(lambda self: self._node._nodeId)
    instance = property(lambda self: self.valueData['instance'])
    dmgDevice = property(lambda self: self._node._ozwmanager._getDmgDevice(self))
    lastUpdate = property(lambda self: self._lastUpdate)
    valueData = property(lambda self: self._valueData)
    labelDomogik = property(lambda self: self._getLabelDomogik())
    isPolled = property(lambda self:self._node._manager.isPolled(self.valueData['id']))

    def getMemoryUsage(self):
        """Renvoi l'utilisation memoire de la value en octets"""
        return sys.getsizeof(self) + sum(sys.getsizeof(v) for v in self.__dict__.values())

    def getValue(self, key):
        """Retourne la valeur du dict valueData correspondant à key"""
        return self.valueData[key] if self._valueData.has_key(key) else None

    def HandleSleepingSetvalue(self):
        """Gère un akc eventuel pour un device domogik et un node sleeping."""
        if self._node.isSleeping and self.getDomogikDevice() is not None:
            sensor_msg = self.valueToSensorMsg()
            if sensor_msg :
                self._node._ozwmanager._cb_send_sensor(sensor_msg)

    def RefreshOZWValue(self):
        """Effectue une requette pour rafraichir la valeur réelle lut par openzwave"""
        if self._valueData['genre'] != 'Config' :
            if self._node._manager.refreshValue(self.valueData['id']):
                self.log.debug(u"++++++++++ Node {0} Request a RefreshOZWValue : {1}".format(self.valueData['nodeId'],  self.valueData['label']))
                return True
        else :
            self.log.debug(u"RefreshOZWValue : call requestConfigParam waiting ValueChanged...")
            self._node._manager.requestConfigParam(self.homeId,  self.nodeId,  self.valueData['index'])
            return True
        return False

    def getCmdClassAssociateValue(self):
        """retourn la commandClass, son Label et son instance qui peut-etre associé à un type bouton ou autre."""
        # TODO: Ajouter les acciociations spéciques du type button en fonction des commandClass.
        retval = None
        if self.valueData['type'] == 'Button':
            if self.valueData['commandClass']  in ['COMMAND_CLASS_SWITCH_MULTILEVEL']:
                if self.labelDomogik in ['dim', 'bright'] :
                    retval = {'commandClass': self.valueData['commandClass'],  'label': 'level', 'instance': self.valueData['instance']}
            self.log.debug(u"A type button return his associate value : {0}".format(retval))
        return retval

    def setValue(self, val):
        """Envois sur le réseau zwave le 'changement' de valeur à la valueNode
            Retourne un dict {
                value : valeur envoyée
                error : texte de l'erreur éventuelle }
        """
        self.log.debug(u"Set Value of type : {0}".format(type (val)))
        button = False
        retval = {'value': False,  'error':  '' }
        if self.valueData['genre'] != 'Config' or self.valueData['type'] == 'List' : # TODO: Pas encore de gestion d'une config en type list, force envoie par setvalue
            if self.valueData['type'] == 'Bool':
                value = False if val in [False, 'FALSE', 'False',  'false', '',  0,  0.0, (),  [],  {},  None ] else True
                val = value
                self.log.debug(u"set value conversion {0} ({1}) to {2} ({3})".format(type(value), value, type(val), val))
            elif self.valueData['type'] == 'Byte' :
                try: value = int(val)
                except ValueError, ex:
                    value = self.valueData['value']
                    raise OZwaveValueException('setvalue byte : {0}'.format(ex))
            elif self.valueData['type'] == 'Decimal' :
                try :value = float(val)
                except ValueError, ex:
                    value = self.valueData['value']
                    raise OZwaveValueException('setvalue Decimal : {0}'.format(ex))
            elif self.valueData['type'] == 'Int' :
                try: value = int(val)
                except ValueError, ex:
                    value = self.valueData['value']
                    raise OZwaveValueException('setvalue Int : {0}'.format(ex))
            elif self.valueData['type'] == 'List' : value = str(val)
            elif self.valueData['type'] == 'Schedule' :
                try: value = int(val)  # TODO: Corriger le type schedule dans setvalue
                except ValueError, ex:
                    value = self.valueData['value']
                    raise OZwaveValueException('setvalue Shedule : {0}'.format(ex))
            elif self.valueData['type'] == 'Short' :
                try: value = long(val)
                except ValueError, ex:
                    value = self.valueData['value']
                    raise OZwaveValueException('setvalue Short : {0}'.format(ex))
            elif self.valueData['type'] == 'String' : value = str(val)
            elif self.valueData['type'] == 'Button' : # TODO: type button set value ?
                button = True
                value = bool(val)
                retval ['value']   = val
                if val :
                    ret = self._node._manager.pressButton(self.valueData['id'])
                    self.log.debug(u"Set value a type button , presscommand : {0}".format(val))
                else :
                    ret = self._node._manager.releaseButton(self.valueData['id'])
                    self.log.debug(u"Set value a type button , releasecommand :".format(val))
                if not ret :
                    retval ['error']   = 'Value is not a Value Type_Button.'
            else : value = val
            self.log.debug(u"setValue of {0} instance : {1}, value : {2}, type : {3}".format(self.valueData['commandClass'],
                                        self.valueData['instance'], value, self.valueData['type']))
            if not button :
                if not self._node._manager.setValue(self.valueData['id'], value)  :
                    self.log.error (u"setValue return bad type : {0}, instance :{1}, value : {2}, on valueId : {3}".format(self.valueData['commandClass'],
                                            self.valueData['instance'],  val, self.valueData['id']))
                    retval ['value'] = False
                    retval['error'] = "Return bad type value."
                else :
                    self._valueData['value'] = val
                    self._lastUpdate = time.time()
                    retval ['value'] = val
        else :
            if not self._node._manager.setConfigParam(self.homeId,  self.nodeId,  self.valueData['index'], int(val))  :
                self.log.error (u"setConfigParam no send message : {0}, index :{1}, value : {2}, on valueId : {3}".format(self.valueData['commandClass'],
                                        self.valueData['index'],  val, self.valueData['id']))
                retval ['value'] = False
                retval['error'] = "setConfigParam : no send message."
            else :
                self._valueData['value'] = val
                self._lastUpdate = time.time()
                retval ['value'] = val
        if self.valueData['genre'] == 'Config' :
            self._node._manager.requestConfigParam(self.homeId,  self.nodeId,  self.valueData['index'])
            self.log.debug(u"setValue : call requestConfigParam...")
        report = {'Value' : str(self),  'report': retval}
        self._node.updateLastMsg('setValue', self.valueData)
        self._node._ozwmanager.monitorNodes.nodeChange_report(self.homeId, self.nodeId, report)
        if retval['error'] == '' :
            self.HandleSleepingSetvalue()
            self._node.requestOZWValue(self.getCmdClassAssociateValue())
        return retval

    def updateData(self, valueData):
        """valueData update from callback argument. return true/false if value is different from old."""
        if self._tempConv and valueData['label'].lower() == 'temperature' and valueData['units'] == 'F': # TODO: Conversion forcée de F en °C, a mettre en option.
            valueData['units'] = '°C'
            self.log.debug(u"************** Conversion : {0}".format(float(valueData['value'])))
            self.log.debug(u"{0}".format(float(valueData['value'])*(5.0/9)))
            valueData['value'] = (float(valueData['value'])*(5.0/9))-(160.0/9)
            self.log.debug("{0}".format(valueData['value']))
        new = True if self._valueData['value'] != valueData['value'] else False
        self._valueData.update(dict(valueData))
        self._realValue = self._valueData['value']
        self._lastUpdate = time.time()
        valueData['homeId'] = int(valueData['homeId']) # Pour etre compatible avec javascript
        valueData['id'] = str(valueData['id']) # Pour etre compatible avec javascript
        self._node.reportToUI({'type': 'value-changed', 'usermsg' :'Value has changed.', 'data': valueData})
        return new

    def convertInType(self,  val):
        """Convertion de val dans le type de la value."""
        retval = val
        valT = type(val)
        selfT = type(self._valueData['value'])
        if valT in [int , long, float, complex, bool] :
            if selfT == bool : retval = bool(val)
            elif selfT == int : retval = int(val)
            elif selfT == long : retval = long(val)
            elif selfT == float : retval = float(val)
            elif selfT == complex : retval = complex(val)
        elif  valT == str :
            if selfT == bool :
                Cval = val.capitalize()
                retval = True if Cval in ['', 'True',  'T',  'Yes',  'Y'] else False
            elif selfT == int : retval = int(val)
            elif selfT == long : retval = long(val)
            elif selfT == float : retval = float(val)
            elif selfT == complex : retval = complex(val)
        return retval

    def _getDmgUnitFromZW(self):
        """Return unit string convert to domogik DT_Type used"""
        if self._valueData['units'].lower() == "seconds" : return "s"
        elif self._valueData['units'].lower() == "c" : return "°C"
        elif self._valueData['units'].lower() == "f" : return "°F"
        return self._valueData['units']

    def _getLabelDomogik(self):
        """ Return OZW label formated in lowcase."""
        retval = self.valueData['label'].lower()
        return retval

    def getDataTypesFromZW(self):
        """ Return all datatype name(s) possibilities depending of zwave value parameters.
            Depending of Label, Type and Units.
        """
#        for DType in self._node._ozwmanager._dataTypes :
        if self._valueData['type'] == 'Bool':
            # DT_Bool and childs DT_Switch, DT_Enable, DT_Binary, DT_Step, DT_UpDown, DT_OpenClose, DT_Start, DT_State
            if self.labelDomogik == 'switch' :
                return ['DT_Switch']
            return ['DT_Bool', 'DT_Enable', 'DT_Binary', 'DT_Step', 'DT_UpDown', 'DT_OpenClose', 'DT_Start', 'DT_State']
        elif self._valueData['type'] in ['Byte', 'Decimal', 'Int', 'Short', 'List', 'Schedule', 'String', 'Button'] :
            if self._valueData['readOnly'] : # value set as sensor
                sensors = self._node._ozwmanager.getSensorByName(self.labelDomogik)
                types =[]
                unit = self._getDmgUnitFromZW()
                if sensors :
                    for sensor in sensors :
                        if unit != "" :
                            if 'unit' in sensors[sensor] :
                                if sensors[sensor]['unit'] == unit :
                                    types.append(sensors[sensor]['data_type'])
                        else :
                            if not 'unit' in sensors[sensor] or not sensors[sensor]['unit'] :
                                types.append(sensors[sensor]['data_type'])
                    return types
            else : # value set as command
                cmds = self._node._ozwmanager.getCommandByName(self.labelDomogik)
                types =[]
                if cmds :
                    for cmd in cmds :
                        for param in cmds[cmd]['parameters'] : types.append(param['data_type'])
                return types
        return []

    def getDomogikDevice(self):
        """Determine si la value peut être un device domogik et retourne le format du nom de device"""
        retval = None
        if (self.valueData['commandClass'] in CmdsClassAvailable) and (self.labelDomogik in DomogikLabelAvailable) :
            retval = self._node._ozwmanager.getDmgDevRefFromZW(self)
        return retval

    def getDmgSensor(self):
        """Return Sensor of domogik device corresponding to value"""
        dmgDevice = self.dmgDevice
        sensors = {}
        labelDomogik = self.labelDomogik
        if dmgDevice is not None :
            for sensor in dmgDevice['sensors']:
                if dmgDevice['sensors'][sensor]['name'].lower() == labelDomogik :
                    # handle praticular labels
                    if labelDomogik == 'temperature' : # °C, F, K
                        if dmgDevice['sensors'][sensor]['data_type'] in self.getDataTypesFromZW():
                            sensors[sensor] = dmgDevice['sensors'][sensor]
                    else : # generic labels
                        sensors[sensor] = dmgDevice['sensors'][sensor]
            if sensors :
                if len(sensors) > 1 :
                    self.log.warning(u"More than one compatibility of domogik sensor. Device_type : {0}, sensors : {1}".format(dmgDevice['device_type_id'], sensors))
                return sensors
        return sensors

    def getDmgCommand(self):
        """Return Command of domogik device corresponding to value"""
        dmgDevice = self.dmgDevice
        labelDomogik = self.labelDomogik
        cmds = {}
        if dmgDevice is not None :
            for cmd in dmgDevice['commands']:
                for param in dmgDevice['commands'][cmd] :
                    if param['key'].lower() == labelDomogik :
                        # handle praticular labels
                        # generic labels
                        cmds[cmd] = dmgDevice['commands'][cmd]
                if cmds :
                    if len(sensors) > 1 :
                        self.log.warning(u"More than one compatibility of domogik commmand. Device_type : {0}, sensors : {1}".format(dmgDevice['device_type_id'], sensors))
                return cmds
        return {}

    def getInfos(self):
        """ Retourne les informations de la value , format dict{} """
        retval = {}
        retval = dict(self.valueData)
        retval['homeId'] = int(retval['homeId']) # Pour etre compatible avec javascript
        retval['id'] = str(retval['id']) # Pour etre compatible avec javascript
        retval['domogikdevice']  = self.getDomogikDevice()
        retval['help'] = self.getHelp()
        retval['polled'] = self.isPolled
        retval['pollintensity'] = self.getPollIntensity()
        retval['listelems'] = list(self.getListItems()) if (self.valueData['type'] == 'List') else None
        retval['realvalue'] = self._realValue
        return retval

    def getValueItemStr(self):
        """Retourne la string selectionnée dans la liste des valeurs possible pour le type list"""
        retval = ""
        if self.valueData['type'] == 'List':
            retval = self._node._manager.getValueListSelectionStr(self.valueData['id'])
        return retval

    def getValueItemNum(self):
        """Retourne la string selectionnée dans la liste des valeurs possible pour le type list"""
        retval = None
        if self.valueData['type'] == 'List':
            retval = self._node._manager.getValueListSelectionNum(self.valueData['id'])
        return retval

    def getListItems(self):
        """Retourne la liste des valeurs possible pour le type list"""
        retval = set()
        if self.valueData['type'] == 'List':
            retval = self._node._manager.getValueListItems(self.valueData['id'])
        return retval

    def getHelp(self):
        """Retourne l'aide utilisateur concernant la fonctionnalité du device"""
        return self._node._manager.getValueHelp(self.valueData['id'])

    def enablePoll(self, intensity = 1):
        """Enable the polling of a device's state.

            :param id: The ID of the value to start polling
            :type id: int
            :param intensity: The intensity of the poll
            :type intensity: int
            :return: True if polling was enabled.
            :rtype: bool"""
        try :
            intensity = int(intensity)
        except Exception as e:
            self.log.error(u'value.enablePoll(intensity) :' + e.message)
            return {"error" : "Enable poll, error : %s" %e.message}
        if self.isPolled :
            self.setPollIntensity(intensity)
            return True
        else : return self._node._manager.enablePoll(self.valueData['id'], intensity)

    def disablePoll(self):
        """Disable polling of a value.

            :param id: The ID of the value to disable polling.
            :type id: int
            :return: True if polling was disabled.
            :rtype: bool """
        return self._node._manager.disablePoll(self.valueData['id'])

    def getPollIntensity(self):
        """Get the intensity with which this value is polled (0=none, 1=every time through the list, 2-every other time, etc).
            :param id: The ID of a value.
            :type id: int
            :return: A integer containing the poll intensity
            :rtype: int"""
        #TODO: A réactiver dans la libopenzwave.pyx
        return self._node._manager.getPollIntensity(self.valueData['id'])

    def setPollIntensity(self, intensity):
        """Set the frequency of polling (0=none, 1=every time through the set, 2-every other time, etc)

            :param id: The ID of the value whose intensity should be set
            :type id: int
            :param intensity: the intensity of the poll
            :type intensity: int"""
        self._node._manager.setPollIntensity(self.valueData['id'], intensity)

    def valueToSensorMsg(self):
        """Return formated message for MQ depending of command_class value.
                {
                network-id = The network ID of primary controller node, should be in association with HomeID (Could be directly HomeID)
                node =  The node number
                instance = The instance number
                type = The Label openzwave (property : ZWaveValueNode.labelDomogik)
                current = new current value of sensor
                }
        """
        # TODO: Traiter le formattage en fonction du type de message à envoyer à domogik rajouter ici le traitement pour chaque command_class
        # Ne pas modifier celles qui fonctionnent mais rajouter. la fusion ce fera après implémentation des toutes les command-class.
        # Le schema est toujours sensor.basic ou alarm.basic, meme pour les commandes puisque le xpl-trig est destiné au OK et à un sensor.
        sensorMsg = None
        device =  self.getDomogikDevice()
        if device is not None :
            dmgDevice = self.dmgDevice
            print dmgDevice
            sensorMsg = {'typexpl':'xpl-trig', 'schema': 'sensor.basic', 'device': device}
            if self.valueData['commandClass'] == 'COMMAND_CLASS_SWITCH_BINARY' :
                if self.valueData['type'] == 'Bool' :
                    if self.valueData['value']  in ['False', False] : current = 'Off'
                    elif  self.valueData['value'] in ['True',  True] : current = 'On'
                    else : raise OZwaveValueException("Error format in valueToSensorMsg : %s" %str(sensorMsg))
                    sensorMsg['data'] =  {'type': self.labelDomogik, 'current': current}
            elif self.valueData['commandClass'] == 'COMMAND_CLASS_SWITCH_MULTILEVEL' :
                if self.valueData['type']  == 'Byte' and self.valueData['label']  == 'Level' :  # cas d'un module type dimmer, gestion de l'état on/off
                    if self.valueData['value'] == 0:
                        sensorMsg['msgdump'] = {'type': 'switch','current': 'Off'}
                    else : sensorMsg['msgdump']  = {'type': 'switch', 'current': 'On'}
                    sensorMsg['data'] = {'type': self.labelDomogik, 'current': self.valueData['value']}
                elif self.valueData['type']  == 'Button' :                                                        # Cas par exemple d'un "bright" ou "dim, la commande devient le label et transmet une key "value".
                    sensorMsg['data']  = {'type': self.labelDomogik, 'current':  self.valueData['value']}
            elif self.valueData['commandClass'] == 'COMMAND_CLASS_THERMOSTAT_SETPOINT' :
                sensorMsg['data']  = {'type': 'setpoint', 'current': self.valueData['value']}
                if self.valueData['units'] != '': sensorMsg ['data'] ['units'] = self.valueData['units']  # TODO: A vérifier pas sur que l'unit soit util
            elif self.valueData['commandClass'] == 'COMMAND_CLASS_SENSOR_BINARY' :
                if self.valueData['type'] == 'Bool' :
#                    dmgDevice = self.dmgDevice
#                    if dmgDevice is not None :
#                        sensors = self.getDmgSensor(dmgDevice)
#                        if sensors and 'current' in sensors :
#                            dataType = self._node._ozwmanager.getDataType(sensors['current']['data_type'])
#                            if dataType :
#                                current = dataType['labels']['1' if self.valueData['value'] else '0']
#                            else : current = 'True' if self.valueData['value'] else 'False'
#                        else : current = 'True' if self.valueData['value'] else 'False'
#                    else : current = 'True' if self.valueData['value'] else 'False'
                    sensorMsg ['data'] = {'type': self.labelDomogik, 'current' : 1 if self.valueData['value'] else 0}
            elif self.valueData['commandClass'] == 'COMMAND_CLASS_SENSOR_MULTILEVEL' :
                if self.valueData['type'] ==  'Decimal' :   #TODO: A supprimer quand Widget gerera les digits.
                    value = round(self.valueData['value'], 2)
                else:
                    value = self.valueData['value']
                sensorMsg ['data'] = {'type': self.labelDomogik, 'current': value}
                if self.valueData['units'] != '': sensorMsg ['data'] ['units'] = self.valueData['units'] # TODO: A vérifier pas sur que l'unit soit util
            elif self.valueData['commandClass'] == 'COMMAND_CLASS_BATTERY' :
                sensorMsg ['data'] = {'type': self.labelDomogik, 'current':self.valueData['value']}
                if self.valueData['units'] != '': sensorMsg ['data'] ['units'] = self.valueData['units'] # TODO: A vérifier pas sur que l'unit soit util
            elif self.valueData['commandClass'] == 'COMMAND_CLASS_POWERLEVEL' :
                sensorMsg ['data'] = {'type': self.labelDomogik, 'current':self.valueData['value']}
            elif self.valueData['commandClass'] == 'COMMAND_CLASS_METER' :
                if self.valueData['type'] ==  'Decimal' :   #TODO: A supprimer quand Widget gerera les digits.
                    value = round(self.valueData['value'], 2)
                else:
                    value = self.valueData['value']
                sensorMsg ['data'] = {'type' : self.labelDomogik,  'current' : value}
                if self.valueData['units'] != '': sensorMsg ['data'] ['units'] = self.valueData['units'] # TODO: A vérifier pas sur que l'unit soit util
            elif self.valueData['commandClass'] == 'COMMAND_CLASS_ALARM' :
                sensorMsg['schema'] = 'alarm.basic'
                sensorMsg ['data'] = {'type': self.labelDomogik, 'current':self.valueData['value']}
                if self.valueData['units'] != '': sensorMsg ['data'] ['units'] = self.valueData['units'] # TODO: A vérifier pas sur que l'unit soit util
            elif self.valueData['commandClass'] == 'COMMAND_CLASS_SENSOR_ALARM' :  # considère toute valeur != 0 comme True
                sensorMsg['schema'] = 'alarm.basic'
                sensorMsg ['data'] = {'type': self.labelDomogik, 'current' : 'high' if self.valueData['value'] else 'low'} # gestion du sensor binary pour widget binary

        if sensorMsg is not None : self.log.debug(u"*** valueToSensorMsg : {0}".format(sensorMsg))
        else: self.log.debug(u"Value not implemented to xPL : {0}".format(self.valueData['commandClass']))
        return sensorMsg

    def __str__(self):
        return 'homeId: [{0}]  nodeId: [{1}]  valueData: {2}'.format(self.homeId, self.nodeId, self.valueData)
