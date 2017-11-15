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

from  lib.utils import pluginprocess, simplecommand
import os, sys, platform
import zlib
import base64
import traceback
import json
import logging

if sys.platform.startswith('win'):
    from lib.registerwindows import constantregisterwindows
    import _winreg

DEBUGPULSEPLUGIN = 25
ERRORPULSEPLUGIN = 40
WARNINGPULSEPLUGIN = 30
plugin = {"VERSION": "1.4", "NAME" :"inventory", "TYPE":"machine"}

@pluginprocess
def action(xmppobject, action, sessionid, data, message, dataerreur, result):
    logging.log(DEBUGPULSEPLUGIN,"plugin %s"% (plugin))
    if sys.platform.startswith('linux'):
        try:
            finv = os.path.join("/","tmp","inventory.txt")
            simplecommand("fusioninventory-agent  --stdout > %s"%finv)
            Fichier = open(finv, 'r')
            result['data']['inventory'] = Fichier.read()
            Fichier.close()
            result['data']['inventory'] = base64.b64encode(zlib.compress(result['data']['inventory'], 9))
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            raise
    elif sys.platform.startswith('win'):
        try:
            bitness = platform.architecture()[0]
            if bitness == '32bit':
                other_view_flag = _winreg.KEY_WOW64_64KEY
            elif bitness == '64bit':
                other_view_flag = _winreg.KEY_WOW64_32KEY

            # run the inventory
            program = os.path.join(os.environ["ProgramFiles"], 'FusionInventory-Agent', 'fusioninventory-agent.bat')
            namefile = os.path.join(os.environ["ProgramFiles"], 'Pulse', 'tmp', 'inventory.txt')
            cmd = """\"%s\" --local=\"%s\""""%(program, namefile)
            simplecommand(cmd)
            Fichier = open(namefile, 'r')
            result['data']['inventory'] = base64.b64encode(zlib.compress(Fichier.read(), 9))
            Fichier.close()
            # read max_key_index parameter to find out the number of keys
            if hasattr(xmppobject.config, 'max_key_index'):
                result['data']['reginventory'] = {}
                result['data']['reginventory']['info'] = {}
                result['data']['reginventory']['info']['max_key_index'] = int(xmppobject.config.max_key_index)
                nb_iter = int(xmppobject.config.max_key_index) + 1
                # get the value of each key and create the json file
                for num in range(1, nb_iter):
                    reg_key_num = 'reg_key_'+str(num)
                    result['data']['reginventory'][reg_key_num] = {}
                    registry_key = getattr(xmppobject.config, reg_key_num)
                    result['data']['reginventory'][reg_key_num]['key'] = registry_key
                    hive = registry_key.split('\\')[0].strip('"')
                    sub_key = registry_key.split('\\')[-1].strip('"')
                    path = registry_key.replace(hive+'\\', '').replace('\\'+sub_key, '').strip('"')
                    logging.log(DEBUGPULSEPLUGIN, "hive: %s" % hive)
                    logging.log(DEBUGPULSEPLUGIN, "path: %s" % path)
                    logging.log(DEBUGPULSEPLUGIN, "sub_key: %s" % sub_key)
                    reg_constants = constantregisterwindows()
                    try:
                        key = _winreg.OpenKey(reg_constants.getkey(hive),
                                              path,
                                              0,
                                              _winreg.KEY_READ | other_view_flag)
                        key_value = _winreg.QueryValueEx(key, sub_key)
                        logging.log(DEBUGPULSEPLUGIN,"key_value: %s" % str(key_value[0]))
                        result['data']['reginventory'][reg_key_num]['value'] = str(key_value[0])
                        _winreg.CloseKey(key)
                    except Exception, e:
                        logging.log(ERRORPULSEPLUGIN,"Error getting key: %s" % str(e))
                        result['data']['reginventory'][reg_key_num]['value'] = ""
                        pass
                # generate the json and encode
                logging.log(DEBUGPULSEPLUGIN,"---------- Registry inventory Data ----------")
                logging.log(DEBUGPULSEPLUGIN,json.dumps(result['data']['reginventory'], indent=4, separators=(',', ': ')))
                logging.log(DEBUGPULSEPLUGIN,"---------- End Registry inventory Data ----------")
                result['data']['reginventory'] = base64.b64encode(json.dumps(result['data']['reginventory'], indent=4, separators=(',', ': ')))
        except Exception, e:
            logging.log(ERRORPULSEPLUGIN,"Error: %s" % str(e))
            traceback.print_exc(file=sys.stdout)
            raise
    elif sys.platform.startswith('darwin'):
        pass
