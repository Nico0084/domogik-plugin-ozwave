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

Read openzwave lib C++ xml files configurations

@author: Nico <nico84dev@gmail.com>
@copyright: (C) 2007-2013 Domogik project
@license: GPL(v3)
@organization: Domogik
"""
from libopenzwave import PyManager
from ozwdefs import *
from xml.dom import minidom
import sys

class OZwaveConfigException(Exception):
    """"Zwave Manager exception  class"""

    def __init__(self, value):
        Exception.__init__(self, value)
        self.msg = "OZwave XML files exception:"

    def __str__(self):
        """String format object"""
        return repr(self.msg+' '+self.value)

class DeviceProduct():
    """Read and handle individual product file recognized by open-zwave."""

    def __init__(self,  path,  config):
        """Read XML file "product".xml of open-zwave C++ lib"""
        self.xml_file = path + '/'  + config
        self.xml_content = minidom.parse(self.xml_file)
        self.protocol ={}
        for p in self.xml_content.getElementsByTagName("Protocol"):
            try :
                self.protocol = {'nodeinfosupported' : True if p.attributes.get("nodeinfosupported").value.strip() == 'true' else False}
            except:
                self.protocol = {'nodeinfosupported' : True}
            for a in p.getElementsByTagName("APIcall"):
                try :
                    self.protocol['APIcall'] = {'function': int(a.attributes.get("function").value.strip(), 16),
                                                           'present': True if a.attributes.get("present").value.strip() == 'true' else False}
                except : pass
        self.commandsClass = []
        for c in self.xml_content.getElementsByTagName("CommandClass") :
#            cmdClass = {'id' : int(c.attributes.get("id").value.strip())}
            cmdClass ={}
            for k in c.attributes.keys():
                v = c.attributes[k].value
                if v.lower() in ['true', 'false']:
                    v = True if v.lower() == 'true' else False
                else :
                    try :
                        v = int(v)
                    except :
                        try:
                            v = float(v)
                        except : pass
                cmdClass[k] = v
            if cmdClass['id'] == 133 :  #<!-- Association Groups -->
                Associations = []
                try:
                    for a in c.getElementsByTagName("Associations") :
                        groups = []
                        try :
                            for g in a.getElementsByTagName("Group") :
                                group = {"index" : int(g.attributes.get("index").value.strip()),
                                              "max_associations" :  int(g.attributes.get("max_associations").value.strip()),
                                              "label" : g.attributes.get("label").value.strip(),
                                              "auto" : True if g.attributes.get("auto").value.strip() =='true' else False}
                                groups.append(dict(group))
                        except: pass
                        Associations.append(groups)
                except: pass
                cmdClass['associations'] = groups
            elif cmdClass['id'] == 132 :  #<!-- COMMAND_CLASS_WAKE_UP -->
                cmdClass['create_vars'] = c.attributes.get("create_vars").value.strip()
#                print "COMMAND_CLASS_WAKE_UP"
            else :
                values = []
                try:
#                    print cmdClass
                    for v in c.getElementsByTagName("Value") :
#                        print "+++++++",  v.toxml()
                        value = {"type" :  v.attributes.get("type").value.strip(),
                                       "genre" : v.attributes.get("genre").value.strip(),
                                       "index" : int(v.attributes.get("index").value.strip()),
                                       "value" :v.attributes.get("value").value.strip()}
                        try:
                            value["label"] = v.attributes.get("label").value.strip()
                        except: pass
                        try:
                            value["instance"] = int(v.attributes.get("instance").value.strip())
                        except: pass
                        try:
                            value["size"] = int(v.attributes.get("size").value.strip())
                        except: pass
                        try:
                            value["units"] = v.attributes.get("units").value.strip()
                        except: pass
                        try:
                            value["min"] = int(v.attributes.get("min").value.strip()),
                            value["max"] = int(v.attributes.get("max").value.strip()),
                        except: pass
                        try:
                            value["help"] = v.getElementsByTagName("Help")[0].firstChild.data
                        except: pass
                        if value['type'] == 'list' :
                            items = {}
                            for i in v.getElementsByTagName("Item") :
                                items.update({int(i.attributes.get("value").value.strip()) : i.attributes.get("label").value.strip()})
                            value['items'] = items
                        values.append(dict(value))
                except: pass
#                print "********", values
                if values : cmdClass['values'] = values
#            print cmdClass
            self.commandsClass.append(cmdClass)

    def getAllTranslateText(self, tabtext = []):
        """Return tab with all text should be translate"""
        for cmdC in self.commandsClass :
            for item in cmdC :
                if type(cmdC[item]) == list :
                    for i in cmdC[item] :
                        if type(i) == dict :
                            for t in i :
                                if type(i[t]) in [unicode,  str]:
                                    try :
                                        int(i[t])
                                    except :
                                        if i[t] not in tabtext :
                                            tabtext.append(i[t])
        return tabtext

    def getProductData(self):
        """Return a list with product data"""
        data = {'protocol': self.protocol}
        data['commandClasses'] = self.commandsClass
        return data

class Manufacturers():
    """Read and handle list of manufacturers and products recognized by open-zwave."""

    def __init__(self,  path):
        """Read XML file manufacturer_specific.xml of open-zwave C++ lib"""
        self.path = path
        self.xml_file = "manufacturer_specific.xml"
        self.xml_content = minidom.parse(path + "/" + self.xml_file)
        # read xml file
        self.manufacturers = [];
        self.xmlns = self.xml_content.getElementsByTagName("ManufacturerSpecificData")[0].attributes.get("xmlns").value.strip()
#        print self.xmlns
        for m in self.xml_content.getElementsByTagName("Manufacturer"):
            item = {'id' : int(m.attributes.get("id").value.strip(), 16),  'name' : m.attributes.get("name").value.strip()}
            products = []
            try:
                for p in m.getElementsByTagName("Product"):
                    product = {"type" :  int(p.attributes.get("type").value.strip(), 16),
                                       "id" : int(p.attributes.get("id").value.strip(), 16),
                                       "name" :p.attributes.get("name").value.strip()}
                    try:
                        product["config"] = p.attributes.get("config").value.strip()
                    except: pass
                    products.append(product)
           #         print "  -",  product
            except: pass
            if products != [] :
                item["products"] = products
            self.manufacturers.append(item)
     #  print self.manufacturers

    def getMemoryUsage(self):
        """Renvoi l'utilisation memoire en octets"""
        return sys.getsizeof(self) + sum(sys.getsizeof(v) for v in self.__dict__.values()) + sys.getsizeof(self.xml_content)

    def getManufacturer(self, manufacturer):
        """Return Manufacturer and products if is recognized by name or id."""
        retval = None
        try :
            int(manufacturer,  16)
            ref= 'id'
        except:
            ref = 'name'
        for m in self.manufacturers :
            if m[ref] == manufacturer :
                retval = m
                break
        return retval

    def searchProduct(self,  product):
        """Return Product and Manufacturer if product is find."""
        retval = []
        for m in self.manufacturers:
            mf = None
            try:
                for p in m['products']:
                    if product in p['name'] :
                        if not mf : mf = {'id': m['id'],  'name': m['name'],  'products': []}
                        mf['products'].append(p)
            except: pass
            if mf : retval.append(mf)
        return retval

    def getProduct(self,  name) :
        """Return all informations of a product."""
        products = self.searchProduct(name)
        if products[0] :
#            print products[0]['products'][0]
            if products[0]['products'][0].has_key('config') :
                return DeviceProduct(self.path, products[0]['products'][0]['config'])
            else : return None
        else :
            return None

    def searchProductType(self,  type,  id = None):
        """Return Product and Manufacturer if product is find."""
        retval = []
        type = int(type, 16)
        if id : id = int(id, 16)
        for m in self.manufacturers:
            mf = None
            try:
                for p in m['products']:
                    if type == int(p['type'], 16) and (not id or (id == int(p['id'],  16))) :
                        if not mf : mf = {'id': m['id'],  'name': m['name'],  'products': []}
                        mf['products'].append(p)
            except: pass
            if mf : retval.append(mf)
        return retval

    def getAllProductsName(self):
        """Retourn all products recognized without doublon."""
        manufacturers = []
        for m in self.manufacturers:
            products=[]
            try:
                for p in m['products']:
                    newP = True
                    if p.has_key('config') : conf = p['config']
                    else : conf =""
                    for rP in products :
                        if p['name'] == rP['name'] and conf == rP['config'] :
                   #     i = products.index(p['name']).index(p['id'])
                            rP['ids'].append(p['id'])
                            newP = False
                    if newP :
                  # if i = p['name'] not in products :
                        prod = {'name': p['name'], 'type': p['type'], 'ids': [p['id']]}
                        prod.update({'config': conf})
                        products.append(prod)
            except: pass
            manufacturers.append({'manufacturer': m['name'], 'id': m['id'], 'products': products})
        return manufacturers

    def getAllProductsTranslateText(self):
        tabtext=[]
        products=[]
        productsName=[]
        for m in self.manufacturers:
            try:
                for p in m['products'] :
                    if p['name'] not in productsName :
                        productsName.append(p['name'])
                        products.append(p)
                    if p.has_key('config') :
                        prod = DeviceProduct(self.path, p['config'])
                        if prod : prod.getAllTranslateText(tabtext)
            except: pass
        return {'products':products, 'tabtext' : tabtext}

class NetworkFileConfig():
    """Read and manage open-zwave xml zwave Network composing"""

    def __init__(self,  path):
        """Read XML file zwcfg_<HOMEID>.xml of open-zwave C++ lib"""
        self.xml_file = path

        self.xml_content = minidom.parse(self.xml_file)
        # read xml file
        self.nodes = []
        self.drivers = []
        for a in self.xml_content.getElementsByTagName("Driver"):
            driver = {'version': a.attributes.get("version").value.strip()}
            driver['homeId'] = long(a.attributes.get("home_id").value.strip(), 16)
            driver['nodeId'] = int(a.attributes.get("node_id").value.strip())
            driver['apiCapabilities'] = int(a.attributes.get("api_capabilities").value.strip())
            driver['controllerCapabilities'] = int(a.attributes.get("controller_capabilities").value.strip())
            driver['pollInterval'] = int(a.attributes.get("poll_interval").value.strip())
            try : # handle openzwave version int or boolean
                driver['pollIntervalBetween'] = int(a.attributes.get("poll_interval_between").value.strip())
            except :
                driver['pollIntervalBetween'] = True if a.attributes.get("poll_interval_between").value.strip()== "true" else False
            self.drivers.append(driver)
        for n in self.xml_content.getElementsByTagName("Node"):
            item = {'id' : int(n.attributes.get("id").value.strip())}
#            print n ,  item['id']
            try :
                item['name'] = n.attributes.get("name").value.strip()
                item['location'] = n.attributes.get("location").value.strip()
                item['basic'] = int(n.attributes.get("basic").value.strip())
                item['generic'] = int(n.attributes.get("generic").value.strip())
                item['specific'] = int(n.attributes.get("specific").value.strip())
                item['type'] = n.attributes.get("type").value.strip()
                item['listening'] = True if n.attributes.get("listening").value.strip() == "true" else False
                item['frequentListening'] = True if n.attributes.get("frequentListening").value.strip() == "true" else False
                item['beaming'] = True if n.attributes.get("beaming").value.strip() == "true" else False
                item['routing'] = True if n.attributes.get("routing").value.strip() == "true" else False
                item['max_baud_rate'] = int(n.attributes.get("max_baud_rate").value.strip())
                item['version'] = int(n.attributes.get("version").value.strip())
                item['query_stage'] = n.attributes.get("query_stage").value.strip()
            except : pass
            try :
                item['security'] = True if n.attributes.get("security").value.strip() == "true" else False
            except:
                item['security'] = False
            try :
                item['nodeinfosupported'] = True if n.attributes.get("nodeinfosupported").value.strip() == "true" else False
            except:
                item['nodeinfosupported'] = True
            try :
                m = n.getElementsByTagName('Manufacturer')[0]
                item['manufacturer'] = {'id' : int(m.attributes.get("id").value.strip(), 16),
                                                    'name' : m.attributes.get("name").value.strip(), }
                item['product'] = {'type' :int(m.getElementsByTagName('Product')[0].attributes.get("type").value.strip(), 16),
                                            'id' : int(m.getElementsByTagName('Product')[0].attributes.get("id").value.strip(), 16),
                                            'name' :m.getElementsByTagName('Product')[0].attributes.get("name").value.strip(), }
            except : pass
            cmdsClass = []
            try:
#                print ("--------- Search cmds class :",  item['product']['name'])
                for c in n.getElementsByTagName("CommandClass"):
                    cmdClass = {"id" : int(c.attributes.get("id").value.strip())}
                    try:
                        cmdClass["version"] =  int(c.attributes.get("version").value.strip())
                    except: pass
                    try:
                        cmdClass["name"] = c.attributes.get("name").value.strip()
                    except: pass
                    try:
                        cmdClass["action"] = c.attributes.get("action").value.strip()
                    except: pass
                    try:
                        cmdClass["base"] = c.attributes.get("base").value.strip()
                    except: pass
                    try:
                        cmdClass["override_precision"] = int(c.attributes.get("override_precision").value.strip())
                    except: pass
                    try:
                        cmdClass["create_vars"] =  True if c.attributes.get("create_vars").value.strip() == "true" else False
                    except: pass
                    try:
                        cmdClass["setasreport"] = True if c.attributes.get("setasreport").value.strip() == "true" else False
                    except: pass
                    try:
                        cmdClass["ignoremapping"] = True if c.attributes.get("ignoremapping").value.strip() == "true" else False
                    except: pass
                    try:
                        cmdClass["getsupported"] = True if c.attributes.get("getsupported").value.strip() == "true" else False
                    except: pass
                    try:
                        cmdClass["classgetsupported"] = True if c.attributes.get("classgetsupported").value.strip() == "true" else False
                    except: pass
                    try:
                        cmdClass["request_flags"] = int(c.attributes.get("request_flags").value.strip())
                    except: pass
                    try:
                        cmdClass["endpoints"] = c.attributes.get("endpoints").value.strip()
                    except: pass
                    try:
                        cmdClass["mapping"] = int(c.attributes.get("mapping").value.strip())
                    except: pass
                    try:
                        cmdClass["codes"] = c.attributes.get("codes").value.strip()
                    except: pass
                    try :
                        instances = []
                        for i in c.getElementsByTagName("Instance"):
                            instance = {'index': int(i.attributes.get("index").value.strip())}
                            try :
                                instance['endpoint'] = int(i.attributes.get("endpoint").value.strip())
                            except: pass
                            instances.append(instance)
                        cmdClass["instances"] = instances
                    except: pass
                    if cmdClass['id'] == 133 :  #<!-- Association Groups -->
                        Associations = {}
                        try:
                            for a in c.getElementsByTagName("Associations") :
                                Associations["num_groups"] = int(a.attributes.get("num_groups").value.strip())
                                Associations["groups"] = []
                                groups = []
                                try :
                                    for g in a.getElementsByTagName("Group") :
                                        group = {"index" : int(g.attributes.get("index").value.strip()),
                                                      "max_associations" :  int(g.attributes.get("max_associations").value.strip()),
                                                      "label" :  u"{0}".format(g.attributes.get("label").value.strip()),
                                                      "auto" : g.attributes.get("auto").value.strip(),
                                                      "nodes" : []}
                                        for n in g.getElementsByTagName("Node"):
                                            group["nodes"].append(int(n.attributes.get("id").value.strip()))
                                        groups.append(dict(group))
                                except: pass
                                Associations["groups"]= groups
                        except: pass
                        cmdClass['associations'] = Associations
                    try:
                        values =[]
                        for v in c.getElementsByTagName("Value"):
                            value = {}
                            try:
                                for k in v.attributes.keys():
                                    value[k] = v.attributes.get(k).value.strip()
                                if value["type"] == 'list':
                                    items = []
                                    for i in v.getElementsByTagName("Item"):
                                        items.append({"label": i.attributes.get("label").value.strip(),
                                                                "value": int(i.attributes.get("value").value.strip())})
                                    value["items"] = items
                                try:
                                    value["help"] = v.getElementsByTagName("Help")[0].firstChild.data
                                except: pass
                                values.append(value)
                            except:
                                print "*** error on decoding {0} : {1} ".format(item['product']["name"],  v.attributes.get("label").value.strip())
                                print value
                                for a in v.attributes.keys(): print "attribute : ", a
                                pass
                        cmdClass["values"] = values
                    except: pass
                    try:
                        sensorMaps = []
                        for sM in c.getElementsByTagName("SensorMap"):
                            sensorMaps.append({"index": int(sM.attributes.get("index").value.strip()), "type": int(sM.attributes.get("type").value.strip())})
                        if sensorMaps :
                            cmdClass["sensorMaps"] = sensorMaps
                    except : pass
                    cmdsClass.append(cmdClass)
            except: pass
            if cmdsClass != [] :
                item["cmdsClass"] = cmdsClass
            if item.has_key("product"): self.nodes.append(item)
#        print self.nodes

    def listeNodes(self):
        retval = []
        for node in self.nodes:
            retval.append(node['id'])
        return retval

    def getNode(self,  nodeId):
        for node in self.nodes:
            if node['id'] == nodeId : return node
        return None

    def getDriver(self, num):
        if self.drivers :
           if num < len(self.drivers):
               return self.drivers[num]
        return None

class DeviceClasses:
    """Read and manage open-zwave device_classes.xml."""

    def __init__(self,  path):
#        import pprint

        """Read XML device_classes.xml of open-zwave C++ lib"""
        self.xml_file = path + "/device_classes.xml"

        self.xml_content = minidom.parse(self.xml_file)
        # read xml file
        self.clssBasic = []
        self.clssGeneric = []
        for a in self.xml_content.getElementsByTagName("DeviceClasses"):
            xmlns = a.attributes.get("xmlns").value.strip()
        for a in self.xml_content.getElementsByTagName("Basic"):
            self._extractXmlData(a)
            self.clssBasic.append(self._extractXmlData(a))
        for a in self.xml_content.getElementsByTagName("Generic"):
            item = self._extractXmlData(a)
            item['Specific'] = []
            try :
                for s in a.getElementsByTagName("Specific"):
                    item['Specific'] .append(self._extractXmlData(s))
            except :
                pass
            self.clssGeneric.append(item)
        self.roles = []
        for a in self.xml_content.getElementsByTagName("Role"):
            self.roles.append(self._extractXmlData(a))
        self.nodeTypes = []
        for a in self.xml_content.getElementsByTagName("NodeType"):
            self.nodeTypes.append(self._extractXmlData(a))
        self.deviceTypes = []
        for a in self.xml_content.getElementsByTagName("DeviceType"):
            self.deviceTypes.append(self._extractXmlData(a))

#        print "*********************"
#        print self.clssBasic
#        print "*********************"
#        pprint.pprint(self.clssGeneric)
#        print "*********************"
#        pprint.pprint(self.roles)
#        print "*********************"
#        print self.nodeTypes
#        print "*********************"
#        pprint.pprint(self.deviceTypes)

    def _extractXmlData(self, a):
        item = {'key' : a.attributes.get("key").value.strip()}
        item['label'] = a.attributes.get("label").value.strip()
        # optional
        try :
            item['command_classes'] = []
            cmdClass = a.attributes.get("command_classes").value.strip().split(',')
            for clss in cmdClass :
                item['command_classes'].append(u"{0} - {1}".format(clss, PyManager.COMMAND_CLASS_DESC[int(clss, 16)]))
        except :
            item['command_classes'] = []
        try :
            item['basic'] = s.attributes.get("basic").value.strip()
        except :
            item['basic'] = u""
        return item

    def getBasic(self, id):
        idNum = id
        if not isinstance(id, int) :
            idNum = int(id,  16)
        for c in self.clssBasic:
            if int(idNum) == int(c['key'], 16) : return c
        return {'key': id, 'label': u'Undefined Basic type'}

    def getGeneric(self, id):
#        import pprint
        idNum = id
        if not isinstance(id, int) :
            idNum = int(id,  16)
        for c in self.clssGeneric:
            if int(idNum) == int(c['key'], 16) :
#                pprint.pprint(c)
                return c
        return {'key': id,
                'label': u'Undefined Generic type',
                'Specific': [{
                    'command_classes': [],
                    'basic': '',
                    'key': u'0x00',
                    'label': u'Not used'
                    }],
                'command_classes': [u''],
                'basic': u''
                }

    def getSpecific(self, generic, id):
#        import pprint
        idNum = id
        g = self.getGeneric(generic)
        if g['label'] != u'Undefined Generic type' :
            if not isinstance(generic, int) :
                generic = int(generic,  16)
            if not isinstance(id, int) :
                idNum = int(id,  16)
    #        print "****** find :", generic,  id
            for g in self.clssGeneric:
                if int(generic) == int(g['key'], 16) :
    #                print "****** generic trouvé : "
    #                pprint.pprint(g)
                    for s in g['Specific']:
    #                    print '****** cherche dans :', s
                        if int(idNum) == int(s['key'], 16) :
    #                        print '********* Spécific trouvé :'
    #                        pprint.pprint(s)
                            return s
            return {'key': id, 'label': u'Undefined Specific type', 'command_classes': [], 'basic': u''}
        else :
            return {'key': id, 'label': g['label'] + u" {0}, Specific can't be find".format(g['key']), 'command_classes': [], 'basic': u''}

    def getRole(self, id):
        idNum = id
        if not isinstance(id, int) :
            idNum = int(id,  16)
        for item in self.roles:
            if int(idNum) == int(item['key'], 16) : return item
        return {'key': id, 'label': u'Undefined Role type', 'command_classes': [], 'basic': u''}

    def getNodeType(self, id):
        idNum = id
        if not isinstance(id, int) :
            idNum = int(id,  16)
        for item in self.nodeTypes:
            if int(idNum) == int(item['key'], 16) : return item
        return {'key': id, 'label': u'Undefined Node type', 'command_classes': [], 'basic': u''}

    def getDeviceTypes(self, id):
        idNum = id
        if not isinstance(id, int) :
            idNum = int(id,  16)
        for item in self.deviceTypes:
            if int(idNum) == int(item['key'], 16) : return item
        return {'key': id, 'label': u'Undefined Device type', 'command_classes': [], 'basic': u''}

    def GetMandatoryCommandClasses(self, classList):
        mClass = []
        for cls in classList :
            pass



if __name__ == "__main__":
    print sys.platform
#    ozw_path = "/home/admdomo/python-openzwave/openzwave/config"
#    ozw_conf = "/home/admdomo/Partage-VM/domogik-plugin-ozwave/data/zwcfg_0x014d0f18.xml"
#    trans_file = "/var/tmp/exporttrad.txt"

    ozw_path ="C:\Python_prog\Dev_OZW\openzwave\config"
    ozw_conf = "C:\Python_prog\domogik-plugin-ozwave\data\zwcfg_0x01ff11ff.xml"
    trans_file = "C:/Python_prog/test/exporttrad.txt"

#    ozw_path="C:\Domotique\python-openzwave\openzwave\config"
#    ozw_conf ="M:\domogik-plugin-ozwave\data\zwcfg_0x01ff11ff.xml"
#    trans_file ="M:\domogik-plugin-ozwave\data\exporttrad.txt"

    listManufacturers = Manufacturers(ozw_path)
#    print listManufacturers.getManufacturer('0x86')
#    print listManufacturers.searchProduct('Thermostat')
#    print '*************** searchProductType'
#    print listManufacturers.searchProductType('0x0400',  '0x0106')
    tabtext = listManufacturers.getProduct('FGS211 Switch 3kW').getAllTranslateText()
    listNodes = NetworkFileConfig(ozw_conf)
    toTranslate = listManufacturers.getAllProductsTranslateText()
    fich = open(trans_file,  "w")
#    for prod in  toTranslate['products']:
#        print prod
#        fich.write(prod['name'].encode('utf8').replace('\n','\r') + '\n\n')
    for ligne in toTranslate['tabtext']:
        fich.write(ligne.encode('utf8').replace('\n','\r') + '\n\n')
    fich.close()

#    print listNodes.getDriver(0)

    deviceClass = DeviceClasses(ozw_path)
#    prod =  listManufacturers.getProduct('FGWPE Wall Plug')
#    print prod.__dict__
    print "*************GetProductDATA***************"
    print
#    print prod.getProductData()
    print 'Basic', deviceClass.getBasic(6)
    print 'Generic',  deviceClass.getGeneric(6)
    print 'Specific', deviceClass.getSpecific(200, '0x01')
    print 'Role', deviceClass.getRole(6)
    print 'NodeType', deviceClass.getNodeType(4)
    print 'DeviceTypes', deviceClass.getDeviceTypes("0x0600")
