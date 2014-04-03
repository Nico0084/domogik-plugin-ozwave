#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
sys.path.append("/var/lib/domogik")


from time import sleep
from domogik_packages.xpl.lib.ozwave import OZWavemanager
from domogik.xpl.common.plugin import XplPlugin


class Log():
    def __init__(selfs):
        print "log actif"
        
    def info(self,  *arg):
        print (arg)
    
    def error(self,  *arg):
        print (arg)
        
def zcallback(self,  *args):
    # callback order: (notificationtype, homeid, nodeid, ValueID, groupidx, event)    
        print "callback"
     #   print type
        print "detail"
        print args
        print "suite"
        print('\n%s\n[%s]:\n' % ('-'*20, args['notificationType']))

def send_xPL(write):
        """ Envoie une commande zwave vers XPL"""
        # TODO : a implémenter pour les sénarios zwave entre module ?
        pass
        
def sendxPL_trig(sread):
        pass
        
def get_stop():
        pass
        
if __name__ == "__main__":
    log=Log()
    ozm= OZWavemanager(send_xPL, sendxPL_trig, get_stop(), log, ozwlog="")
    ozm.openDevice("/dev/zwave")           
    ozm.start()
    a = "True"
    on = "False"
    sleep(15)
    print "******* GO *****"
    while  a == "True":
        print "xxxxxxxxxxxx"
        if ozm.homeId() != None :
            print "Manufact node 1: "+ ozm._manager.getNodeManufacturerName(int(ozm.homeId()), 1)
            print "Manufact node 5: "+ ozm._manager.getNodeManufacturerName(int(ozm.homeId()), 5)
            print "     node 5 Name: "+ ozm._manager.getNodeName(int(ozm.homeId()), 5)
            print "Manufact node 6: "+ ozm._manager.getNodeManufacturerName(int(ozm.homeId()), 6)
            if  on == "True"  :
                ozm._manager.setNodeOff(ozm._homeId, 5)
                print on
                on = "False"
            else :
                 ozm._manager.setNodeOn(int(ozm.homeId()), 5)
                 print on
                 on ="True"
        
        sleep(10)
    ozm.stop()
