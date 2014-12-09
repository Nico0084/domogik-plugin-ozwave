#!/usr/bin/python
#-*- coding: utf-8 -*-

from domogik.tests.common.helpers import configure, delete_configuration
from domogik.common.utils import get_sanitized_hostname

plugin =  "ozwave"

host_id = get_sanitized_hostname()
delete_configuration("plugin", plugin, host_id)

configure("plugin", plugin,  host_id, "autoconfpath", True)
configure("plugin", plugin,  host_id, "configpath",  "/usr/local/share/python-openzwave/config")
configure("plugin", plugin,  host_id, "cpltmsg", True)
configure("plugin", plugin,  host_id, "ozwlog", True)
configure("plugin", plugin,  host_id, "wsportserver", 40470)
