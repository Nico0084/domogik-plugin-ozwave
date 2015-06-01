# -*- coding: utf-8 -*-

### common imports
from flask import Blueprint, abort
from domogik.common.utils import get_packages_directory
from domogik.admin.application import render_template
from domogik.admin.views.clients import get_client_detail
from jinja2 import TemplateNotFound

### package specific imports
from domogik_packages.plugin_ozwave.admin.views.network_tools import get_zwave_state

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
    networksState = get_zwave_state()
    try:
        #return render_template('{0}.html'.format(page))
        return render_template('plugin_ozwave.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            network_active = '',
            plugin_active = 'controller',
            zw_networks = networksState)

    except TemplateNotFound:
        abort(404)

@plugin_ozwave_adm.route('/controller/<network_id>/<client_id>')
def network_ctrl(client_id, network_id):
    detail = get_client_detail(client_id)
    networkState = get_zwave_state()
    try:
        return render_template('plugin_ozwave_controller.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            plugin_active = 'controller',
            network_active = network_id,
            zw_networks = networkState, 
            network_state = networkState['Controllers'])
    except TemplateNotFound:
        abort(404)
    
