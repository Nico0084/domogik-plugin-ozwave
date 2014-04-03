#!/usr/bin/python
#-*- coding: utf-8 -*-

import json
import sys

from domogik.common.packagejson import PackageJson
from domogik_packages.plugin_ozwave.lib.ozwxmlfiles import networkFileConfig
from domogik_packages.plugin_ozwave.lib.ozwdefs import *

json_file = "/home/domogik/plugins/domogik-plugin-ozwave/info.json"
config_file = "/home/domogik/plugins/domogik-plugin-ozwave/data/zwcfg_0x014d0f18.xml"

data = json.load(open(json_file))
#print data
#print 'Domogik validation ...'
#json_data = PackageJson(path=json_file)
#json_data.validate()
#print 'Fin validation fichier {0}'.format(json_file)

def get_sensors(type, sensors):
    """Search sensors capabilities from json xpl_stats dynamics parameters."""
    add =[]
    for stat in data["xpl_stats"]:
        for static  in data["xpl_stats"][stat]["parameters"]["static"]:
            if static["key"] == "type" :
                if static['value'] == type :
                    for sensor in data["xpl_stats"][stat]["parameters"]["dynamic"]:
#                        print "verifie :",  sensor["sensor"],  type
                        if not sensor["sensor"]  in sensors :
                            add.append(sensor["sensor"])
                            sensors = sensors + add
        if add : break
    return  sensors

def get_cmds(type, commands):
    """Search commands capabilities from json commands parameters."""
    add =[]
    for cmd in data["commands"]:
        for key  in data["commands"][cmd]["parameters"]:
#            print "verifie :",  cmd,  type
            if key["key"] == type:
                if not cmd  in commands :
                    add.append(cmd)
                    commands = commands + add
#                    print commands,  cmd
        if add : break
    return  commands

def get_device_type(device):
    """Search for an existing device_types from json device_types."""
    find  = None
    if not device or (device == {}) : 
        print "No specific openzwave parameters cant't handle detection"
        return None
#    print data["device_types"]
    for dev in data["device_types"]:
        find = {dev : data["device_types"][dev]}
        sensors = list(data["device_types"][dev]["sensors"])
        commands = list(data["device_types"][dev]["commands"])
#        print " handle device_type : {0}, sensors : {1}, commands {2}".format(dev, sensors,  commands)
        for sensor in device["sensors"]:
#            print " --- search sensor : ",sensor
            if sensor in sensors:
#                print sensors,  " *** find"
                sensors.remove(sensor)
            else :
                find = None
                break
        if find :
            for command in device["commands"]:
#                print " --- search command : ", command
                if  command in commands:
#                    print commands,  " *** find"
                    commands.remove(command)
                else :
                    find = None
                    break
        if find and (sensors == []) and (commands == []): break
        else : 
            find = None
#            print "     {0} Not corresponding, pass".format(dev)
    return find
    
def get_product(productName):
    """Search for existing product"""
    for prod in data["products"]:
        if productName == prod["name"]:
            return prod
    return None
    
def check_device_type(devJSON,  prodOZWV):
    """Check if product OZW corresponding to product JSON"""
    if not devJSON : return False
    sensors = list(devJSON["sensors"])
    for i in prodOZWV:
        for sensor in prodOZWV[i]["sensors"]:
            if sensor in sensors:
                sensors.remove(sensor)
                break
            else :return False
    commands = list(devJSON["commands"] )
    for i in prodOZWV:
        for command in prodOZWV[i]["commands"]:
            if command in commands:
                commands.remove(command)
                break
            else : return False
    return True

def get_device_type_from_product(product):
    """Return the device_types corresponding to product"""
    if data["device_types"].has_key(product["type"]):
        return data["device_types"][product["type"]]
    else: return None
    
ozw_config = networkFileConfig(config_file)
for node in ozw_config.nodes :
 #   print node,  "/n"
    print"********************************************************"
    print node["product"]["name"]
    product = get_product(node["product"]["name"])
    if product : 
        print "Product detected in json : type :{0}, id : {1}".format(product["type"],  product["id"])
#    print json.dumps(node, sort_keys=True, indent=4)
#    print node
    if node.has_key("cmdsClass") :
        instances ={}
        for cmdClass in node["cmdsClass"] :
 #           print ("********",  cmdClass["name"])
            for v in cmdClass["values"] :
                labeldomogik = v['label'].lower().replace(" ", "-")
#                print " %%%% label : {0}".format(labeldomogik)
                if labeldomogik in DomogikTypeAvailable:
                    if not instances.has_key(v['instance']):
#                        print "add instance",  v['instance']
                        instances[v['instance']] = {'sensors': [], 'commands': []}
#                        print instances
 #                   print ("+++++++ must be a device_types ++++++")
                    instances[v['instance']]["sensors"] = get_sensors(labeldomogik,  instances[v['instance']]["sensors"])
                    instances[v['instance']]["commands"] = get_cmds(labeldomogik,  instances[v['instance']]["commands"])
        print "Devices detection process for : ",  json.dumps(instances, sort_keys=True, indent=4) 
        device = {"sensors":[],  "commands":[]}
        for i in instances:
            device["sensors"].extend(instances[i]["sensors"])
            device["commands"].extend(instances[i]["commands"])
        dev_type = get_device_type(device)
        if dev_type :
            print " ++ device_type detected in json : {0}".format(json.dumps(dev_type, sort_keys=True, indent=4))
        else :
            print " -- No device_type in json for {0}".format(device)
        if product:
            print "Check product : {0}".format(check_device_type(get_device_type_from_product(product), instances))
