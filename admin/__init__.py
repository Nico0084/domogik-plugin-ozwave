# -*- coding: utf-8 -*-

### common imports
from flask import Blueprint, abort
from domogik.common.utils import get_packages_directory
from domogik.admin.application import render_template
from domogik.admin.views.clients import get_client_detail
from jinja2 import TemplateNotFound

### package specific imports
from domogik_packages.plugin_ozwave.admin.views.network_tools import get_manager_state, get_openzwave_info, get_controller_state, get_controller_nodes

### common tasks
package = "plugin_ozwave"
template_dir = "{0}/{1}/admin/templates".format(get_packages_directory(), package)
static_dir = "{0}/{1}/admin/static".format(get_packages_directory(), package)

plugin_ozwave_adm = Blueprint(package, __name__,
                        template_folder = template_dir,
                        static_folder = static_dir)
                        
### package specific functions

@plugin_ozwave_adm.route('/<client_id>')
def index(client_id):
#    client_id = "plugin-ozwave.vmdomogik0"
    detail = get_client_detail(client_id)
    if detail["status"] == "alive" :
        openzwaveInfo = get_openzwave_info()
        managerState = get_manager_state()
    elif detail["status"] == "starting" :
        openzwaveInfo = {u'PYOZWLibVers': u'Plugin starting, please wait...', u'ConfigPath': u'undefined', u'UserPath': u'not init', u'Options' : {}, u'error': u''}
        managerState = {u'OZWPluginVers': u'undefined', u'Controllers': [], u'Init': u'unknown', u'state': u'dead', u'error': u''}
    else :
        openzwaveInfo = {u'PYOZWLibVers': u"Plugin not running, can't get informations.", u'ConfigPath': u'undefined', u'UserPath': u'not init', u'Options' : {}, u'error': u''}
        managerState = {u'OZWPluginVers': u'undefined', u'Controllers': [], u'Init': u'unknown', u'state': u'dead', u'error': u''}
    try:
        #return render_template('{0}.html'.format(page))
        return render_template('plugin_ozwave.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            network_active = '',
            plugin_active = 'controller',
            openzwaveInfo = openzwaveInfo,
            managerState = managerState, 
            network_state = {})

    except TemplateNotFound:
        abort(404)

@plugin_ozwave_adm.route('/<client_id>/<network_id>/controller')
def network_ctrl(client_id, network_id):
    detail = get_client_detail(client_id)
    managerState = get_manager_state()
    openzwaveInfo = get_openzwave_info()
    networkState = get_controller_state(network_id)
    try:
        return render_template('plugin_ozwave_controller.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            plugin_active = 'controller',
            network_active = network_id,
            openzwaveInfo = openzwaveInfo,
            managerState = managerState, 
            network_state = networkState)
            
    except TemplateNotFound:
        abort(404)
    
@plugin_ozwave_adm.route('/<client_id>/<network_id>/nodes')
def network_nodes(client_id, network_id):
    detail = get_client_detail(client_id)
    managerState = get_manager_state()
    openzwaveInfo = get_openzwave_info()
    networkState = get_controller_state(network_id)
    nodesState = get_controller_nodes(network_id)
    try:
        return render_template('plugin_ozwave_nodes.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            plugin_active = 'nodes',
            network_active = network_id,
            openzwaveInfo = openzwaveInfo,
            managerState = managerState, 
            network_state = networkState, 
            nodes_state = nodesState)
            
    except TemplateNotFound:
        abort(404)
