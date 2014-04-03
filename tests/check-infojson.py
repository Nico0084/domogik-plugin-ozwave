#!/usr/bin/python
#-*- coding: utf-8 -*-

import json
import sys
from domogik.common.packagejson import PackageJson

#json_file = "d:\Python_prog\domogik-plugin-daikcode\info.json"
json_file = "/home/admdomo/Partage-VM/domogik-plugin-ozwave/info.json"

data = json.load(open(json_file))
print data
print 'Domogik validation ...'
p = PackageJson(path=json_file)
p.validate()
print 'Fin validation fichier {0}'.format(json_file)
