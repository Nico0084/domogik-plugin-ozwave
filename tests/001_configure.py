#!/usr/bin/python
#-*- coding: utf-8 -*-

from domogik.tests.common.helpers import configure, delete_configuration
from domogik.common.utils import get_sanitized_hostname

plugin =  "ozwave"

host_id = get_sanitized_hostname()
delete_configuration("plugin", plugin, host_id)

configure("plugin", plugin,  host_id, "autoconfpath", "Y")
configure("plugin", plugin,  host_id, "configpath",  "")
configure("plugin", plugin,  host_id, "cpltmsg", "Y")
configure("plugin", plugin,  host_id, "ozwlog", "Y")
