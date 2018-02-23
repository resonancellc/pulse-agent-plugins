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

from  lib.utils import simplecommand
import json
import traceback
import sys, os
import logging

plugin = {"VERSION": "1.0", "NAME" : "asynchromeremoteshell", "TYPE" : "all"}


def action(objectxmpp, action, sessionid, data, message, dataerreur):
    logging.getLogger().debug("###################################################")
    logging.getLogger().debug("call %s from %s"%(plugin,message['from']))
    logging.getLogger().debug("###################################################")
    print json.dumps(data, indent =4);
    result = {
                    'action': "result%s"%action,
                    'sessionid': sessionid,
                    'data' : {},
                    'ret' : 0,
                    'base64' : False
                }
    try:
        obj = simplecommand(data['command'])

        ####obj['result'] = [x.rstrip('\n') for x in  obj['result'] if x != "\n"]
        result['ret'] = 0
        result['data']['code'] = obj['code']
        result['data']['result'] = [ x.strip(os.linesep) for x in obj['result'] ]
        objectxmpp.send_message(    mto=message['from'],
                                    mbody=json.dumps(result, sort_keys=True, indent=4),
                                    mtype='chat')
    except Exception as e:
        logging.getLogger().error(str(e))
        traceback.print_exc(file=sys.stdout)
        dataerreur['ret'] = -255
        dataerreur['data']['msg'] = "Erreur commande\n %s"%data['cmd']
        objectxmpp.send_message(mto=message['from'],
                                mbody=json.dumps(dataerreur),
                                mtype='chat')
