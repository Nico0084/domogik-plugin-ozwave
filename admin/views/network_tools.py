# -*- coding: utf-8 -*-
from domogik.admin.application import app, render_template
from domogik.common.utils import get_sanitized_hostname

from domogikmq.reqrep.client import MQSyncReq
from domogikmq.message import MQMessage

def get_zwave_state():
    cli = MQSyncReq(app.zmq_context)
    msg = MQMessage()
    msg.set_action('ozwave.networks.get')
    res = cli.request('plugin-ozwave.{0}'.format(get_sanitized_hostname()), msg.get(), timeout=10)
    if res is not None:
        zw_networks = res.get_data()
    else:
        zw_networks = {'PYOZWLibVers':'unknown', 'ConfigPath': 'not defined', 'UserPath': 'not init'}
    return zw_networks
