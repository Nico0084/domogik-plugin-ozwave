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

from ozwdefs import *
import time
import sys
import traceback

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
                    'writeOnly': manager.isValueWriteOnly(v),  # Type d'accès lecture/ecriture
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
        self._valueData['writeOnly'] = self._node._manager.isValueWriteOnly(self._valueData['id'])

    # On accède aux attributs uniquement depuis les property
    log = property(lambda self: self._node._ozwmanager._log)
    networkID = property(lambda self: self._node._ozwmanager.getNetworkID(self._node._homeId))
    homeId = property(lambda self: self._node._homeId)
    nodeId = property(lambda self: self._node._nodeId)
    instance = property(lambda self: self._valueData['instance'])
    dmgDevice = property(lambda self: self._node._ozwmanager._getDmgDevice(self))
    lastUpdate = property(lambda self: self._lastUpdate)
    valueData = property(lambda self: self._valueData)
    labelDomogik = property(lambda self: self._getLabelDomogik())
    isPolled = property(lambda self:self._node._manager.isPolled(self._valueData['id']))
    isUpToDate = property(lambda self:self._checkUptoDate())

    def getMemoryUsage(self):
        """Renvoi l'utilisation memoire de la value en octets"""
        return sys.getsizeof(self) + sum(sys.getsizeof(v) for v in self.__dict__.values())

    def getValue(self, key):
        """Retourne la valeur du dict valueData correspondant à key"""
        return self._valueData[key] if self._valueData.has_key(key) else None

    def getDataType(self, name):
        return self._node._ozwmanager.getDataType(name)

    def formatValueDataToJS(self):
        """Format valueData for javascript compatiblity"""
        valueData = dict(self._valueData)
        valueData['homeId'] = int(valueData['homeId']) # int for javascript compatiblity
        valueData['id'] = str(valueData['id']) # str for javascript compatiblity
        valueData['realvalue'] = self._realValue
        return valueData

    def HandleSleepingSetvalue(self):
        """Gère un akc eventuel pour un device domogik et un node sleeping."""
        if self._node.isSleeping and self.getDmgDeviceParam() is not None:
            sensor_msg = self.valueToSensorMsg()
            if sensor_msg :
                self.log.debug(u"Report last sensor message during node sleeping.")
                self._node.reportToUI({'type': 'value-changed', 'usermsg' :'Value has changed.', 'data': self.formatValueDataToJS()})
                self._node._ozwmanager._cb_send_sensor(sensor_msg['device'], sensor_msg['id'], sensor_msg['data_type'], sensor_msg['data']['current'])

    def RefreshOZWValue(self):
        """Effectue une requette pour rafraichir la valeur réelle lut par openzwave"""
        if self._valueData['genre'] != 'Config' :
            if self._node._manager.refreshValue(self._valueData['id']):
                self.log.debug(u"Node {0} Request a RefreshOZWValue : {1}".format(self._valueData['nodeId'], self._valueData['label']))
                return True
        else :
            self.log.debug(u"RefreshOZWValue : call requestConfigParam waiting ValueChanged...")
            self._node._manager.requestConfigParam(self.homeId,  self.nodeId,  self._valueData['index'])
            return True
        return False

    def getCmdClassAssociateValue(self):
        """retourn la commandClass, son Label et son instance qui peut-etre associé à un type bouton ou autre."""
        # TODO: Ajouter les acciociations spéciques du type button en fonction des commandClass.
        retval = None
        if self._valueData['type'] == 'Button':
            if self._valueData['commandClass']  in ['COMMAND_CLASS_SWITCH_MULTILEVEL']:
                if self.labelDomogik in ['dim', 'bright'] :
                    retval = {'commandClass': self._valueData['commandClass'],  'label': 'level', 'instance': self._valueData['instance']}
            self.log.debug(u"A type button return his associate value : {0}".format(retval))
        return retval

    def setValue(self, val):
        """Send on zwave network changing value.
            dict return {
                value : value sended
                error : if text error
                }
        """
        self.log.debug(u"Setting value {0} of {1}".format(val, type (val)))
        button = False
        retval = {'value': False,  'error':  '' }
        if self._valueData['genre'] != 'Config' or self._valueData['type'] == 'List' : # TODO: Pas encore de gestion d'une config en type list, force envoie par setvalue
            if self._valueData['type'] == 'Bool':
                value = False if val in [False, 'FALSE', 'False', 'false', '', '0', 0, 0.0, (), [], {}, None ] else True
                self.log.debug(u"Set value conversion {0} ({1}) to {2} ({3})".format(type(val), val, type(value), value))
            elif self._valueData['type'] == 'Byte' :
                try: value = int(val)
                except ValueError, ex:
                    value = self._valueData['value']
                    raise OZwaveValueException('setvalue byte : {0}'.format(ex))
            elif self._valueData['type'] == 'Decimal' :
                try :value = float(val)
                except ValueError, ex:
                    value = self._valueData['value']
                    raise OZwaveValueException('setvalue Decimal : {0}'.format(ex))
            elif self._valueData['type'] == 'Int' :
                try: value = int(val)
                except ValueError, ex:
                    value = self._valueData['value']
                    raise OZwaveValueException('setvalue Int : {0}'.format(ex))
            elif self._valueData['type'] == 'List' : value = str(val)
            elif self._valueData['type'] == 'Schedule' :
                try: value = int(val)  # TODO: Corriger le type schedule dans setvalue
                except ValueError, ex:
                    value = self._valueData['value']
                    raise OZwaveValueException('setvalue Shedule : {0}'.format(ex))
            elif self._valueData['type'] == 'Short' :
                try: value = long(val)
                except ValueError, ex:
                    value = self._valueData['value']
                    raise OZwaveValueException('setvalue Short : {0}'.format(ex))
            elif self._valueData['type'] == 'String' : value = str(val)
            elif self._valueData['type'] == 'Button' : # TODO: type button set value ?
                button = True
                value = bool(val)
                retval ['value'] = val
                if val :
                    ret = self._node._manager.pressButton(self._valueData['id'])
                    self.log.debug(u"Set value a type button , presscommand : {0}".format(val))
                else :
                    ret = self._node._manager.releaseButton(self._valueData['id'])
                    self.log.debug(u"Set value a type button , releasecommand :".format(val))
                if not ret :
                    retval ['error'] = 'Value is not a Value Type_Button.'
            else : value = val
            self.log.debug(u"Set value of {0} instance : {1}, value : {2}, type : {3}".format(self._valueData['commandClass'],
                                        self._valueData['instance'], value, self._valueData['type']))
            if not button :
                if not self._node._manager.setValue(self._valueData['id'], value)  :
                    self.log.error (u"Set value return bad type : {0}, instance :{1}, value : {2}, on valueId : {3}".format(self._valueData['commandClass'],
                                            self._valueData['instance'], val, self._valueData['id']))
                    retval ['value'] = False
                    retval['error'] = "Return bad type value."
                else :
                    self._valueData['value'] = value
                    self._lastUpdate = time.time()
                    retval ['value'] = val
        else :
            if not self._node._manager.setConfigParam(self.homeId, self.nodeId, self._valueData['index'], int(val))  :
                self.log.error (u"setConfigParam no send message : {0}, index :{1}, value : {2}, on valueId : {3}".format(self._valueData['commandClass'],
                                        self._valueData['index'], val, self._valueData['id']))
                retval ['value'] = False
                retval['error'] = "setConfigParam : no send message."
            else :
                self._valueData['value'] = val
                self._lastUpdate = time.time()
                retval ['value'] = val
        if self._valueData['genre'] == 'Config' :
            self._node._manager.requestConfigParam(self.homeId,  self.nodeId,  self._valueData['index'])
            self.log.debug(u"setValue : call requestConfigParam...")
        report = {'Value' : str(self),  'report': retval}
        self._node.updateLastMsg('setValue', self._valueData)
        self._node._ozwmanager.monitorNodes.nodeChange_report(self.homeId, self.nodeId, report)
        if retval['error'] == '' :
            self.HandleSleepingSetvalue()
            self._node.requestOZWValue(self.getCmdClassAssociateValue())
        return retval

    def updateData(self, valueData):
        """valueData update from callback argument. return true/false if value is different from old."""
        if self._tempConv and valueData['label'] is not None and \
                valueData['label'].lower() == 'temperature' and valueData['units'] == 'F': # TODO: Conversion forcée de F en °C, a mettre en option.
            valueData['units'] = '°C'
            self.log.debug(u"************** Conversion : {0}".format(float(valueData['value'])))
            self.log.debug(u"{0}".format(float(valueData['value'])*(5.0/9)))
            valueData['value'] = (float(valueData['value'])*(5.0/9))-(160.0/9)
            self.log.debug("{0}".format(valueData['value']))
        new = True if self._valueData['value'] != valueData['value'] else False
        self._valueData.update(dict(valueData))
        self._realValue = self._valueData['value']
        self._lastUpdate = time.time()
        self._node.reportToUI({'type': 'value-changed', 'usermsg' :'Value has changed.', 'data': self.formatValueDataToJS()})
        return new

    def convertInType(self,  val):
        """Convertion val in type of value."""
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

    def _checkUptoDate(self):
        """Check if value is up to date with real openzwave and readed directly from ozw node."""
        if self._realValue is not None and self._realValue == self._valueData['value'] : return True
        else : return False

    def _getDmgUnitFromZW(self):
        """Return unit string convert to domogik DT_Type used"""
        if self._valueData['units'].lower() == "seconds" : return u"s"
        elif self._valueData['units'].lower() == "c" : return u"\xb0C"
        elif self._valueData['units'].lower() == "f" : return u"\xb0F"
        return u"{0}".format(self._valueData['units'])

    def _getLabelDomogik(self):
        """ Return OZW label formated in lowcase."""
        if self._valueData['label'] is not None :
            return self._valueData['label'].lower()
        return ''

    def getDataTypesFromZW(self, labelDomogik):
        """ Return all datatype name(s) possibilities depending of zwave value parameters.
            Depending of Label, Type and Units.
        """
#        for DType in self._node._ozwmanager._dataTypes :
        if self._valueData['type'] == 'Bool':
            # DT_Bool and childs DT_Switch, DT_Enable, DT_Binary, DT_Step, DT_UpDown, DT_OpenClose, DT_Start, DT_State
            if labelDomogik == 'switch' :
                return ['DT_Switch']
            return ['DT_Bool', 'DT_Enable', 'DT_Binary', 'DT_Step', 'DT_UpDown', 'DT_OpenClose', 'DT_Start', 'DT_State']
        elif self._valueData['type'] in ['Byte', 'Decimal', 'Int', 'Short', 'List', 'Schedule', 'String', 'Button'] :
            types =[]
            unit = self._getDmgUnitFromZW()
            if not self._valueData['readOnly'] : # value set as command
                cmds = self._node._ozwmanager.getCommandByName(labelDomogik)
                if cmds :
                    for cmd in cmds :
                        for param in cmds[cmd]['parameters'] :
                            dType = self._node._ozwmanager.getDataType(param['data_type'])
                            if unit != "" :
                                if 'unit' in dType :
#                                    self.log.debug(u"    Compare unit cmd {0} <{1}> to {2} <{3}>".format(unit, type(unit), dType['unit'], type(dType['unit'])))
                                    if dType['unit'] == unit :
                                        types.append(param['data_type'])
                            else :
                                if not 'unit' in dType or dType['unit'] == "" :
                                    types.append(param['data_type'])
                                else : types.append(param['data_type']) # force adding data_type if unit is not defined in zwave value
            # value set as sensor
            sensors = self._node._ozwmanager.getSensorByName(labelDomogik)
            self.log.debug (u"   Sensor for label {0} : {1}".format(labelDomogik, sensors))
            if sensors :
#                print (u"")
                for sensor in sensors :
                    dType = self._node._ozwmanager.getDataType(sensors[sensor]['data_type'])
#                    print (u"{0}, {1}".format(dType, unit))
                    if unit != "" :
                        if 'unit' in dType :
#                            print (u"    Compare unit sensor {0} <{1}> to {2} <{3}>".format(unit, type(unit), dType['unit'], type(dType['unit'])))
                            if dType['unit'] == unit :
                                types.append(sensors[sensor]['data_type'])
                    else :
                        if not 'unit' in dType or dType['unit'] == "" :
                            types.append(sensors[sensor]['data_type'])
                        else : types.append(sensors[sensor]['data_type']) # force adding data_type if unit is not defined in zwave value
            return types
        return []

    def getDmgDeviceParam(self):
        """Check if value could be a domogik device and return device name format."""
        retval = None
        labelDomogik = self.labelDomogik
#        logLine = u"*** DomogikLabelAvailable : {0}".format(DomogikLabelAvailable)
#        logLine += u"\n                 *** CmdsClassAvailable :{0}".format(CmdsClassAvailable)
        if self._valueData['commandClass'] in CmdsClassAvailable :
#            logLine += u"         *** CmdClass {0} in CmdsClassAvailable".format(self._valueData['commandClass'])
            if labelDomogik in DomogikLabelAvailable :
                retval = self._node._ozwmanager.getDmgDevRefFromZW(self)
                retval['label'] = labelDomogik
                logLine = u"*** Dmg device Available for {0}.{1}: {2}".format(self.networkID, self.nodeId, retval)
            else :
                for p, linksLabel in self._node._ozwmanager.linkedLabels.iteritems()  :
                    if labelDomogik in linksLabel :
                        retval = self._node._ozwmanager.getDmgDevRefFromZW(self)
                        retval['label'] = p
                        logLine = u"*** Dmg device Available by link for {0} {0}.{2}: {3}".format(labelDomogik, self.networkID, self.nodeId, retval)
                        break
#        if retval is None :
#            logLine = u"*** Dmg device NOT available : {0} - {1}".format(self._valueData['commandClass'], labelDomogik)
        if retval is not None :
            self.log.debug(logLine)
        return retval

    def getDmgSensor(self, labelDomogik):
        """Return Sensor of domogik device corresponding to value"""
        retval = {}
        for dmgDevice in self.dmgDevice:
            logLine = u"+++ Search dmg sensor {0} in dmgDevice {1}".format(labelDomogik, dmgDevice)
            for sensor in dmgDevice['sensors']:
                logLine = u"\n         +++ Compare sensor : {0} with {1}".format(sensor, labelDomogik)
                if self._node.checkAvailableLabel(dmgDevice['sensors'][sensor]['name'].lower(), labelDomogik) :
                    # handle praticular labels
                    if labelDomogik == 'temperature' : # °C, F, K
                        if dmgDevice['sensors'][sensor]['data_type'] in self.getDataTypesFromZW(labelDomogik):
                            retval[sensor] = dmgDevice['sensors'][sensor]
                        retval[sensor] = dmgDevice['sensors'][sensor]
                    else : # generic labels
                        retval[sensor] = dmgDevice['sensors'][sensor]
            if retval :
                if len(retval) > 1:  # more than one sensor find, search good sensor in them."
                    for sensor in retval :
                        if retval[sensor]['name'].lower() == labelDomogik :
                            retval = {sensor: retval[sensor]}
                            break
                    if len(retval) > 1 :
                        self.log.warning(u"Multi Sensor identify for label {0} (source : {1}), can't select one of them : {2}".format(labelDomogik, self.labelDomogik, retval))
                        return {}
                self.log.debug(u"+++ Sensor {0}\n     identified for label {1}".format(retval, labelDomogik))
                return retval
            logLine += u"\n+++     No sensor identified for label {0}".format(labelDomogik)
            self.log.debug(logLine)
        return retval

    def getDmgCommand(self):
        """Return Command of domogik device corresponding to value"""
        labelDomogik = self.labelDomogik
        cmds = {}
        for dmgDevice in self.dmgDevice :
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
        """ Retourn all value informations, format dict{} """
        retval = self.formatValueDataToJS()
        retval['domogikdevice']  = self.getDmgDeviceParam()
        retval['help'] = self.getHelp()
        retval['polled'] = self.isPolled
        retval['pollintensity'] = self.getPollIntensity()
        retval['listelems'] = list(self.getListItems()) if (self._valueData['type'] == 'List') else None
        return retval

    def getValueItemStr(self):
        """Retourne la string selectionnée dans la liste des valeurs possible pour le type list"""
        retval = ""
        if self._valueData['type'] == 'List':
            retval = self._node._manager.getValueListSelectionStr(self._valueData['id'])
        return retval

    def getValueItemNum(self):
        """Retourne la string selectionnée dans la liste des valeurs possible pour le type list"""
        retval = None
        if self._valueData['type'] == 'List':
            retval = self._node._manager.getValueListSelectionNum(self._valueData['id'])
        return retval

    def getListItems(self):
        """Retourne la liste des valeurs possible pour le type list"""
        retval = set()
        if self._valueData['type'] == 'List':
            retval = self._node._manager.getValueListItems(self._valueData['id'])
        return retval

    def getHelp(self):
        """Return help for value device capacity."""
        try :
            return self._node._manager.getValueHelp(self._valueData['id'])
        except :
            self.log.error(u"Get help value error : {0}".format(traceback.format_exc()))
            return "Get help value error : {0}".format(traceback.format_exc())

    def requestConfigParam(self):
        """Send a resquest to get value of command_class_configuration"""
        if self._valueData['commandClass'] == 'COMMAND_CLASS_CONFIGURATION' :
            if not self._valueData['writeOnly'] :
                self._node._manager.requestConfigParam(self.homeId, self.nodeId,  self._valueData['index'])
                report = {'error': "",  'usermsg': u"Node {0} requesting config param values{1} index {0}.".format(self._node.refName, self._valueData['label'],  self._valueData['index'])}
            else : report = {'error': u"Node {0} configuration value {1} index {2} is on write only, can't read real value.".format(self._node.refName, self._valueData['label'],  self._valueData['index'])}
        else : report = {'error':  u"Node {0} configuration value {1} index {2} is not a COMMAND_CLASS_CONFIGURATION, bad request for this value.".format(self._node.refName, self._valueData['label'],  self._valueData['index'])}
        return report

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
        else : return self._node._manager.enablePoll(self._valueData['id'], intensity)

    def disablePoll(self):
        """Disable polling of a value.

            :param id: The ID of the value to disable polling.
            :type id: int
            :return: True if polling was disabled.
            :rtype: bool """
        return self._node._manager.disablePoll(self._valueData['id'])

    def getPollIntensity(self):
        """Get the intensity with which this value is polled (0=none, 1=every time through the list, 2-every other time, etc).
            :param id: The ID of a value.
            :type id: int
            :return: A integer containing the poll intensity
            :rtype: int"""
        return self._node._manager.getPollIntensity(self._valueData['id'])

    def setPollIntensity(self, intensity):
        """Set the frequency of polling (0=none, 1=every time through the set, 2-every other time, etc)

            :param id: The ID of the value whose intensity should be set
            :type id: int
            :param intensity: the intensity of the poll
            :type intensity: int"""
        self._node._manager.setPollIntensity(self._valueData['id'], intensity)

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
        sensorMsg = None
        if self._valueData['commandClass'] == 'COMMAND_CLASS_ALARM' :
            self._node.handleAlarmStep(self)
            return None
        deviceParam =  self.getDmgDeviceParam()
        if deviceParam is not None :
            dmgSensor = self.getDmgSensor(deviceParam['label'])
            if dmgSensor :
                for sensor in dmgSensor :
                    sensorMsg = {'id': dmgSensor[sensor]['id'], 'data_type':  dmgSensor[sensor]['data_type'], 'device': deviceParam}
                    dataType = self.getDataType(dmgSensor[sensor]['data_type'])
                    if self._valueData['commandClass'] == 'COMMAND_CLASS_SWITCH_BINARY' :
                        if self._valueData['type'] == 'Bool' :
                            if self._valueData['value']  in ['False', False] : current = 0
                            elif  self._valueData['value'] in ['True',  True] : current = 1
                            else : raise OZwaveValueException("Error format in valueToSensorMsg : %s" %str(sensorMsg))
                            sensorMsg['data'] =  {'type': self.labelDomogik, 'current': current}
                    elif self._valueData['commandClass'] == 'COMMAND_CLASS_SWITCH_MULTILEVEL' :
                        if self._valueData['type']  == 'Byte' and self._getLabelDomogik() == 'level' :  # cas d'un module type dimmer, gestion de l'état on/off
                            if self._valueData['value'] == 0:
                                sensorMsg['msgdump'] = {'type': 'switch','current': 0}
                            else : sensorMsg['msgdump']  = {'type': 'switch', 'current': 1}
                            sensorMsg['data'] = {'type': self.labelDomogik, 'current': self._valueData['value']}
                        elif self._valueData['type']  == 'Button' :                                                        # Cas par exemple d'un "bright" ou "dim, la commande devient le label et transmet une key "value".
                            sensorMsg['data']  = {'type': self.labelDomogik, 'current':  self._valueData['value']}
                    elif self._valueData['commandClass'] == 'COMMAND_CLASS_THERMOSTAT_SETPOINT' :
                        sensorMsg['data']  = {'type': 'setpoint', 'current': self._valueData['value']}
                        if self._valueData['units'] != '': sensorMsg ['data'] ['units'] = self._valueData['units']  # TODO: A vérifier pas sur que l'unit soit util
                    elif self._valueData['commandClass'] == 'COMMAND_CLASS_SENSOR_BINARY' :
                        if self._valueData['type'] == 'Bool' :
                            sensorMsg ['data'] = {'type': self.labelDomogik, 'current' : 1 if self._valueData['value'] else 0}
                    elif self._valueData['commandClass'] == 'COMMAND_CLASS_SENSOR_MULTILEVEL' :
                        if self._valueData['type'] ==  'Decimal' :   #TODO: A supprimer quand Widget gerera les digits.
                            value = round(self._valueData['value'], 2)
                        else:
                            value = self._valueData['value']
                        sensorMsg ['data'] = {'type': self.labelDomogik, 'current': value}
                        if self._valueData['units'] != '': sensorMsg ['data'] ['units'] = self._valueData['units'] # TODO: A vérifier pas sur que l'unit soit util
                    elif self._valueData['commandClass'] == 'COMMAND_CLASS_BATTERY' :
                        sensorMsg ['data'] = {'type': self.labelDomogik, 'current':self._valueData['value']}
                        if self._valueData['units'] != '': sensorMsg ['data'] ['units'] = self._valueData['units'] # TODO: A vérifier pas sur que l'unit soit util
                    elif self._valueData['commandClass'] == 'COMMAND_CLASS_POWERLEVEL' :
                        sensorMsg ['data'] = {'type': self.labelDomogik, 'current':self._valueData['value']}
                    elif self._valueData['commandClass'] == 'COMMAND_CLASS_METER' :
                        if self._valueData['type'] ==  'Decimal' :   #TODO: A supprimer quand Widget gerera les digits.
                            value = round(self._valueData['value'], 2)
                        else:
                            value = self._valueData['value']
                        sensorMsg ['data'] = {'type' : self.labelDomogik,  'current' : value}
                        if self._valueData['units'] != '': sensorMsg ['data'] ['units'] = self._valueData['units'] # TODO: A vérifier pas sur que l'unit soit util
                    elif self._valueData['commandClass'] == 'COMMAND_CLASS_SENSOR_ALARM' :  # considère toute valeur != 0 comme True
                        sensorMsg ['data'] = {'type': self.labelDomogik, 'current' : 1 if self._valueData['value'] else 0} # gestion du sensor binary pour widget binary
#                        self._node.handleAlarmStep(self)
                    else : sensorMsg = None
                if sensorMsg is not None : self.log.debug(u"Sensor value to Dmg device : {0}".format(sensorMsg))
            else : self.log.debug(u"No sensor find for device {0} - {1}".format(deviceParam, self.labelDomogik))
        else: self.log.debug(u"Sensor value not implemented to Dmg device : {0} - {1}".format(self._valueData['commandClass'], self.labelDomogik))
        return sensorMsg

    def getAlarmSensorMsg(self):
        """Must be call at end of alarm sequence, return value to sensor msg"""
        sensorMsg = None
        deviceParam =  self.getDmgDeviceParam()
        if deviceParam is not None :
            dmgSensor = self.getDmgSensor(deviceParam['label'])
            if dmgSensor :
                for sensor in dmgSensor :
                    sensorMsg = {'id': dmgSensor[sensor]['id'], 'data_type':  dmgSensor[sensor]['data_type'], 'device': deviceParam}
                    if self._valueData['commandClass'] == 'COMMAND_CLASS_ALARM' :
                        vConv = self._node._ozwmanager.getCmdClassLabelConversions('COMMAND_CLASS_ALARM', self.labelDomogik)
                        if self._valueData['type'] == 'List' :
                            value = self.getValueItemStr()
                        else :
                            value = self._valueData['value']
                            for v, vc in vConv.iteritems() :
                                if int(v) == value :
                                    self.log.debug(u"COMMAND_CLASS_ALARM {0}, converted value {1} to {2} for sensor {3}".format(self.labelDomogik, value, vc, dmgSensor[sensor]))
                                    value = vc
                                    break;
                        sensorMsg ['data'] = {'type': self.labelDomogik, 'current': value}
                        if self._valueData['units'] != '': sensorMsg ['data'] ['units'] = self._valueData['units'] # TODO: A vérifier pas sur que l'unit soit util
                    elif self._valueData['commandClass'] == 'COMMAND_CLASS_SENSOR_ALARM' :  # considère toute valeur != 0 comme True
                        sensorMsg ['data'] = {'type': self.labelDomogik, 'current' : 1 if self._valueData['value'] else 0} # gestion du sensor binary pour widget binary
                    else : sensorMsg = None
                if sensorMsg is not None : self.log.debug(u"Sensor value to Dmg device : {0}".format(sensorMsg))
            else : self.log.debug(u"No sensor find for device {0} - {1}".format(deviceParam, self.labelDomogik))
        else: self.log.debug(u"Sensor value not implemented to Dmg device : {0} - {1}".format(self._valueData['commandClass'], self.labelDomogik))
        return sensorMsg

    def __str__(self):
        return 'homeId: [{0}]  nodeId: [{1}]  valueData: {2}'.format(self.homeId, self.nodeId, self._valueData)
