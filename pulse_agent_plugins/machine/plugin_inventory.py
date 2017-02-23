# -*- coding: utf-8 -*-
#
# (c) 2016 siveo, http://www.siveo.net
#
# This file is part of Pulse 2, http://www.siveo.net
#
# Pulse 2 is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Pulse 2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pulse 2; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.

from  lib.utils import pluginprocess
import sys, os
from  lib.utils import simplecommand
import zlib, base64
import traceback
import json
if sys.platform.startswith('win'):
    from lib.registerwindows import constantregisterwindows
    import _winreg

plugin={"VERSION": "1.1", "NAME" :"inventory", "TYPE":"machine"}


@pluginprocess
def action( xmppobject, action, sessionid, data, message, dataerreur, result):
    print "plugin_inventory"
    if sys.platform.startswith('linux'):
        try:
            obj = simplecommand("fusioninventory-agent  --stdout > /tmp/inventory.txt")
            Fichier = open("/tmp/inventory.txt",'r')
            result['data']['inventory'] = Fichier.read()
            Fichier.close()
            result['data']['inventory'] = base64.b64encode(zlib.compress(result['data']['inventory'],9))
        except Exception, e:
            print "Error: %s" % str(e)
            traceback.print_exc(file=sys.stdout)
            raise
    elif sys.platform.startswith('win'):
        try:
            # run the inventory
            program = os.path.join(os.environ["ProgramFiles"],'FusionInventory-Agent','fusioninventory-agent.bat')
            namefile = os.path.join(os.environ["ProgramFiles"], 'Pulse', 'tmp', 'inventory.txt')
            cmd = """\"%s\" --local=\"%s\""""%(program,namefile)
            simplecommand(cmd)
            Fichier = open(namefile,'r')
            result['data']['inventory'] = base64.b64encode(zlib.compress(Fichier.read(), 9))
            Fichier.close()
            # read max_key_index parameter to find out the number of keys
            if hasattr(xmppobject.config, 'max_key_index'):
                result['data']['reginventory'] = {}
                result['data']['reginventory']['info'] = {}
                result['data']['reginventory']['info']['max_key_index'] = int(xmppobject.config.max_key_index)
                nb_iter = int(xmppobject.config.max_key_index) + 1
                # get the value of each key and create the json file
                for num in range(1,nb_iter):
                    reg_key_num = 'reg_key_'+str(num)
                    result['data']['reginventory'][reg_key_num] = {}
                    registry_key = getattr(xmppobject.config,reg_key_num)
                    result['data']['reginventory'][reg_key_num]['key'] = registry_key
                    hive = registry_key.split('\\')[0].strip('"')
                    sub_key = registry_key.split('\\')[-1].strip('"')
                    path = registry_key.replace(hive+'\\','').replace('\\'+sub_key,'').strip('"')
                    print "hive: %s" % hive
                    print "sub_key: %s" % sub_key
                    print "path: %s" % path
                    reg_constants = constantregisterwindows()
                    key = _winreg.OpenKey(reg_constants.getkey(hive), path)
                    (key_value, key_type) = _winreg.QueryValueEx(key,sub_key)
                    result['data']['reginventory'][reg_key_num]['value'] = str(key_value)
                    _winreg.CloseKey(key)
                # generate the json and encode
                result['data']['reginventory'] = base64.b64encode(json.dumps(result['data']['reginventory'], sort_keys=True, indent=4, separators=(',', ': ')))
        except Exception, e:
            print "Error: %s" % str(e)
            traceback.print_exc(file=sys.stdout)
            raise
    elif sys.platform.startswith('darwin'):
        pass
