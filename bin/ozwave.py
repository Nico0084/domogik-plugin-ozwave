#!/usr/bin/python
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
# A debugging code checking import error
try:
    from domogik.xpl.common.xplconnector import Listener
    from domogik.xpl.common.plugin import XplPlugin
    from domogik.xpl.common.xplmessage import XplMessage
    from domogik.xpl.common.xplconnector import XplTimer
    
#    from domogik.xpl.common.queryconfig import Query
    from domogik.mq.reqrep.client import MQSyncReq
    from domogik.mq.message import MQMessage
    
    from domogik_packages.plugin_ozwave.lib.ozwave import OZWavemanager
    from domogik_packages.plugin_ozwave.lib.ozwdefs import OZwaveException
    import threading
    import sys
    import time
except ImportError as exc :
    import logging
    logging.basicConfig(filename='/var/log/domogik/ozwave_start_error.log',level=logging.DEBUG)
    err = "Error: Plugin Starting failed to import module ({})".format(exc) 
    print err
    logging.error(err)

#from domogik_packages.plugin_ozwave.lib.ozwmqworker import OZWMQRep

class OZwave(XplPlugin):
    """ Implement a listener for Zwave command messages
        and launch background  manager to listening zwave events by callback
    """
        
    def __init__(self):
        """ Create listener and background zwave manager
        """
        XplPlugin.__init__(self, name = 'ozwave')
        # check if the plugin is configured. If not, this will stop the plugin and log an error
        if not self.check_configured():
            return
        # get the devices list
        self.devices = self.get_device_list(quit_if_no_device = False)
        # Récupère la config 
        ozwlogConf = self.get_config('ozwlog')
        self.myzwave = None
        self._ctrlHBeat = None
        print ('Mode log openzwave :',  ozwlogConf)
        # Recupère l'emplacement des fichiers de configuration OZW
        pathUser = self.get_data_files_directory()
        pathConfig = self.get_config('configpath') + '/'
        # Initialise le manager Open zwave
        
        try:
            self.myzwave = OZWavemanager(self, self.send_xPL, self.sendxPL_trig, self.get_stop(), self.log, configPath = pathConfig,  userPath = pathUser,  ozwlog = ozwlogConf)
            print 'OZWmanager demarré :-)'
        except Exception as e:
            raise
            self.log.error('Error on creating OZWmanager at 1st attempt : {0} **** try second attempt.'.format(e))
            self.get_stop().wait(2)
            try:
                self.log.debug('try second attempt after 2s.{0}'.format(sys.exc_info()))
                self.myzwave = OZWavemanager(self, self.send_xPL, self.sendxPL_trig, self.get_stop(), self.log, configPath = pathConfig,  userPath = pathUser,  ozwlog = ozwlogConf)
                print 'OZWmanager demarré :-)'
            except Exception as e2:
                self.log.error('Error on creating 2nd attempt OZWmanager : {0}'.format(e2))
                self.force_leave()
                return
                
#        self.log.debug('Opening worker MQ')        
#        self.serverUI = OZWMQRep(self.myzwave.cb_ServerWS, self.log)
#        self.log.debug('worker MQ open')        
#        
                # get the devices list
        self.devices = self.get_device_list(quit_if_no_device = False)
        # Crée le listener pour les messages de commande xPL traités par les devices zwave
        Listener(self.ozwave_cmd_cb, self.myxpl,{'schema': 'ozwave.basic','xpltype': 'xpl-cmnd'})
        # Validation avant l'ouverture du controleur, la découverte du réseaux zwave prends trop de temps -> RINOR Timeout
        self.add_stop_cb(self.myzwave.stop)
        if self._waitForRest() :
            self._ctrlHBeat = XplTimer(60, self.myzwave.sendXplCtrlState, self.myxpl)
            self._ctrlHBeat.start()
            #lancement du thread de démarrage des sercices ozwave
            self.myzwave.starter.start()
            self.log.info('****** Init OZWave xPL manager completed ******')
            self.ready()        
        else : self.force_leave()

        
    def _waitForRest(self):
        """Attends  que le serveur rest http soit disponible, timeout de sortie = 60s"""
        import urllib2
        from domogik.common.configloader import Loader

        cfg_rest = Loader('rest')
        config_rest = cfg_rest.load()
        conf_rest = dict(config_rest[1])
        if conf_rest['use_ssl'] == 'False' : protocol = 'http'
        else : protocol = 'https'
        rest = "%s://%s:%s" % (protocol, config_rest[0]['bind_interface'], conf_rest['port'])
        the_url = "%s" % (rest) #/base/device/list
        rest_ok = False
        time_out = False
        t = time.time()
        while not self.get_stop().isSet() and not time_out and not rest_ok:
            self.log.debug("Try to join rest at :{0}".format(the_url))
            try :
                req = urllib2.Request(the_url)
                handle = urllib2.urlopen(req)
                devices = handle.read()
            except IOError,  e:
                if time.time() - t >= 60 : time_out = True
                else : 
                    self.log.debug("Rest no response, wait 3s for next try. {0}".format(e.reason))
                    self.get_stop().wait(3)
            else : rest_ok = True
        if rest_ok : return True
        else:
            if time_out :
                self.log.error("Rest not response (by timeout) quit plugin :(")
                return False
            else :
                self.log.error("Rest not response (by stop plugin) quit plugin :(")
                return False
   
    def getsize(self):
        return sys.getsizeof(self) + sum(sys.getsizeof(v) for v in self.__dict__.values())

    def ozwave_cmd_cb(self, message):
        """" Envoie la cmd xpl vers le OZWmanager
        xpl-cmnd
        {
        ...
        }
        ozwave.basic
        {
        networkid = The network ID of primary controller node, should be in association with HomeID (Could be directly HomeID)
        node =  The node number
        instance = The instance number
        command = The Label openzwave (property : ZWaveValueNode.labelDomogik)
        value = new value of command
        }
        """
        print ("commande xpl recue")
        print message
        self.log.debug(message)
        if self.myzwave is not None and self.myzwave.monitorNodes is not None : self.myzwave.monitorNodes.xpl_report(message)
        if 'command' in message.data: # TODO:  A supprimer faire avec MQ.
            if 'group'in message.data:
                # en provenance de l'UI spéciale
                self.ui_cmd_cb(message)
            else :
                device = self.myzwave.getZWRefFromxPL(message.data)
                if device :
                    self.myzwave.sendNetworkZW(device, message.data['command'], message.data['value'])
                else :
                    self.log.warning("Zwave command not sended : {0}".format(message))
                    
    def getdict2UIdata(self, UIdata):
        """ retourne un format dict en provenance de l'UI (passage outre le format xPL)"""
        retval = UIdata.replace('&quot;', '"').replace('&squot;', "'").replace("&ouvr;", '{').replace("&ferm;", '}') ;
        try :
            return eval(retval)
        except Exception as e:
            print retval
            self.log.debug ("Format data to UI : eval in getdict2UIdata error : " +   retval)
            return {'error': 'invalid format'}
            
    def getUIdata2dict(self, ddict):
        """Retourne le dict formatter pour UI (passage outre le format xPL)"""
        print "conversion pour transfertvers UI , " , str(ddict)
        for k in ddict :   # TODO: pour passer les 1452 chars dans RINOR, à supprimer quand MQ OK, 
            if isinstance(ddict[k], str) :
                ddict[k] = ddict[k].replace("'", "&squot;")  # remplace les caractères interdits pour rinor
                if len(str(ddict[k])) >800 : 
                    ddict[k] = ddict[k][:800]
                    print("value raccourccis : ", k, ddict[k])
                    self.log.debug ("Format data to UI : value to large, cut to 800, key : %s, value : %s" % (str(k), str(ddict[k])))
        return str(ddict).replace('{', '&ouvr;').replace('}', '&ferm;').replace('"','&quot;').replace("'",'&quot;').replace('False', 'false').replace('True', 'true').replace('None', '""')
     

    def on_mdp_request(self, msg):
        # display the req message
        print(msg)
        XplPlugin.on_mdp_request(self, msg)
        # call a function to reply to the message depending on the header
        action = msg.get_action().split(".")
        handled = False  
        print action
        if action[0] == 'ozwave' :
            self.log.debug(u"Handle MQ request action <{0}>.".format(action))
            if action[1] == "networks" :# "ozwave.networks.get":
                if action[2] == "get" :
                    handled = True
                    req = {'header':{'type': 'req'}, 'request': 'GetNetworkID'} # TODO remove header key it's just for starting with less modif
                    report = self.myzwave.cb_ServerWS(req)
                    print report
                    # send the reply
                    msg = MQMessage()
                    msg.set_action('ozwave.networks.get')
                    for k, item in report.items():
                        msg.add_data(k, item)
                    print msg.get()
                    self.reply(msg.get())
            if not handled :
                self.log.warning(u"MQ request unknown action <{0}>.".format(action))

    def ui_cmd_cb(self, message):
        """xpl en provenace de l'UI (config/special)"""
        response = True
        info = "essais"
        request = self.getdict2UIdata(message.data['value'])
        print("Commande UI")
        if message.data['group'] =='UI' :
            mess = XplMessage()
            mess.set_type('xpl-trig') 
            mess.set_schema('ozwave.basic')
            if request['request'] == 'ctrlAction' :
                action = dict(request)
                del action['request']
                report = self.myzwave.handle_ControllerAction(action)
                info = self.getUIdata2dict(report)
                mess.add_data({'command' : 'Refresh-ack', 
                                    'group' :'UI', 
                                    'ctrlaction' : request['action'], 
                                    'data': info})
                if request['cmd'] =='getState' and report['cmdstate'] != 'stop' : response = False
            elif request['request'] == 'ctrlSoftReset' :
                info = self.getUIdata2dict(self.myzwave.handle_ControllerSoftReset())
                mess.add_data({'command' : 'Refresh-ack', 
                                    'group' :'UI', 
                                    'data': info})
            elif request['request'] == 'ctrlHardReset' :
                info = self.getUIdata2dict(self.myzwave.handle_ControllerHardReset())
                mess.add_data({'command' : 'Refresh-ack', 
                                    'group' :'UI', 
                                    'data': info})   
            elif request['request'] == 'GetPluginInfo' :
                info = self.getUIdata2dict(self.myzwave.getPluginInfo())
                mess.add_data({'command' : 'Refresh-ack', 
                                    'group' :'UI', 
                                    'node' : 0, 
                                    'data': info})
            else :
                mess.add_data({'command' : 'Refresh-ack', 
                                    'group' :'UI', 
                                    'data': "unknown request", 
                                    'error': "unknown request"})
                print "commande inconnue"
            if response : self.myxpl.send(mess)
                                  
                                    
    def send_xPL(self, xPLmsg,  args = None):
        """ Envoie une commande ou message zwave vers xPL"""
        # TODO: Vérifier le format xpl d'adresse du device
        mess = XplMessage()
        mess.set_type(xPLmsg['type']) 
        mess.set_schema(xPLmsg['schema'])
        if xPLmsg.has_key('data') : mess.add_data(xPLmsg['data'])
        if args :
            mess.add_data({'data': self.getUIdata2dict(args)})
        print mess
        self.log.debug("************ sending xPL :{0}, {1} : {2}".format(mess.type, mess.schema, mess.data)) 
        self.myxpl.send(mess)
        if self.myzwave is not None and self.myzwave.monitorNodes is not None : self.myzwave.monitorNodes.xpl_report(mess)
        
    def sendxPL_trig(self, msgtrig):
        """Envoie un message trig sur le hub xPL"""
        mess = XplMessage()
        messDup = None
        # TODO: Récupérer le format xpl d'adresse du device
        if 'info' in msgtrig:
            self.log.error ("Error : Node %s unreponsive" % msgtrig['node'])
        elif 'Find' in msgtrig:
            print("node enregistré : %s" % msgtrig['Find'])
        elif 'typexpl' in msgtrig :
            print "sendxPL_trig  +++++++++++++++++++ ", msgtrig
            mess.set_type(msgtrig['typexpl'])
            mess.set_schema(msgtrig['schema'])
            mess.add_data(msgtrig['device'])
            mess.add_data(msgtrig['data'])                            
            if msgtrig.has_key('msgdump'): 
                messDup = msgtrig['msgdump']
                messDup['device'] = msgtrig['device']
            print mess
            self.myxpl.send(mess)
            if self.myzwave is not None : self.myzwave.monitorNodes.xpl_report(mess)
            if messDup : # envoi d'un message dupliqué avec des keys differentes (pour un dimmer le level sur on/off)
                mess.clear_data()
                mess.add_data(messDup)
                print 'Dump Xpl Message : ' + str(mess)
                self.myxpl.send(mess)
                if self.myzwave is not None :  self.myzwave.monitorNodes.xpl_report(mess)
        elif 'command' in msgtrig and msgtrig['command'] == 'Info':
            print("Home ID is %s" % msgtrig['Home ID'])
            
    def publishMsg(self, category, content):
        self._pub.send_event(category, content)
        self.log.debug(u"Publishing over MMQ <{0}>, data : {1}".format(category, content))

if __name__ == "__main__":
    OZwave()
