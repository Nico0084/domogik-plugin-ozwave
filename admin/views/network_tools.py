# -*- coding: utf-8 -*-
from domogik.admin.application import app, render_template
from domogik.common.utils import get_sanitized_hostname

from domogikmq.reqrep.client import MQSyncReq
from domogikmq.message import MQMessage

def get_openzwave_info():
    cli = MQSyncReq(app.zmq_context)
    msg = MQMessage()
    msg.set_action('ozwave.openzwave.get')
    res = cli.request('plugin-ozwave.{0}'.format(get_sanitized_hostname()), msg.get(), timeout=10)
    if res is not None:
        data = res.get_data()
    else:
        data = {u'status': u'dead', u'PYOZWLibVers':u'unknown', u'ConfigPath': u'undefined', 'uUserPath': u'not init', u'Options' : {}, u'error': u'Plugin timeout response.'}
    return data
    
def get_manager_state():
    cli = MQSyncReq(app.zmq_context)
    msg = MQMessage()
    msg.set_action('ozwave.manager.get')
    res = cli.request('plugin-ozwave.{0}'.format(get_sanitized_hostname()), msg.get(), timeout=10)
    if res is not None:
        data = res.get_data()
    else:
        data = {u'status': u'dead', u'OZWPluginVers': u'undefined', u'Controllers': [], u'Init': u'unknown', u'state': u'dead', u'error': u'Plugin timeout response.'}
    return data

def get_controller_state(networkId):
    cli = MQSyncReq(app.zmq_context)
    msg = MQMessage()
    msg.set_action('ozwave.controller.get')
    msg.add_data('networkId', networkId)
    res = cli.request('plugin-ozwave.{0}'.format(get_sanitized_hostname()), msg.get(), timeout=10)
    if res is not None:
        data = res.get_data()
    else:
        data = {u'NetworkID': u'unknown', u'Node': 1, u'Init_state': u'unknown', u'Node count': 0, u'Protocol': u'unknown',
                               u'Node sleeping': 0, u'ListNodeId': [], u'Library': u'undefined', u'state': u'dead', u'Version': u'undefined',
                               u'error': u'Plugin timeout response.', u'HomeID': u'undefined', u'Primary controller': u'undefined', u'Model': u'undefined', u'Poll interval': 0}
    return data

def get_controller_nodes(networkId):
    cli = MQSyncReq(app.zmq_context)
    msg = MQMessage()
    msg.set_action('ozwave.controller.nodes')
    msg.add_data('networkId', networkId)
    res = cli.request('plugin-ozwave.{0}'.format(get_sanitized_hostname()), msg.get(), timeout=10)
    if res is not None:
        data = res.get_data()
    else:
        data = {u'NetworkID': u'unknown', u'Node': 1, u'Init_state': u'unknown', u'Node count': 0, u'Protocol': u'unknown',
                               u'Node sleeping': 0, u'ListNodeId': [], u'Library': u'undefined', u'state': u'dead', u'Version': u'undefined',
                               u'error': u'Plugin timeout response.', u'HomeID': u'undefined', u'Primary controller': u'undefined', u'Model': u'undefined', u'Poll interval': 0}
    return data
