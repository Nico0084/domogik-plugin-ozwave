#!/usr/bin/python
#-*- coding: utf-8 -*-

from domogik.tests.common.helpers import configure, delete_configuration
from domogik.common.utils import get_sanitized_hostname

plugin =  "ozwave"

host_id = get_sanitized_hostname()
delete_configuration("plugin", plugin, host_id)

configure("plugin", plugin,  host_id, "autoconfpath", "Y")
configure("plugin", plugin,  host_id, "configpath",  "/usr/local/lib/python2.7/dist-packages/libopenzwave-0.3.0b4-py2.7-linux-x86_64.egg/config")
configure("plugin", plugin,  host_id, "cpltmsg", "Y")
configure("plugin", plugin,  host_id, "ozwlog", "Y")
