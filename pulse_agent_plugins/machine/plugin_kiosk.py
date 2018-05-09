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

import logging
import json
import traceback
import sys

plugin = {"VERSION": "1.0", "NAME" : "kiosk", "TYPE" : "machine"}


def action(objectxmpp, action, sessionid, data, message, dataerreur):
    logging.getLogger().debug("=====================================================")
    logging.getLogger().debug(plugin)
    logging.getLogger().debug("=====================================================")
    datasend = {'action' : "result%s"%plugin['NAME'],
                'data' :{'subaction' : 'test'},
                'sessionid' : sessionid
               }
    try:
        if data['subaction'] == 'test':
            datasend['data']['msg'] = "test success"
            objectxmpp.send_message(mto=message['from'],
                                    mbody=json.dumps(datasend, sort_keys=True, indent=4),
                                    mtype='chat')
        elif data['subaction'] == 'listpackage':
            #todo
            pass

    except:
        traceback.print_exc(file=sys.stdout)
        dataerreur['ret'] = -255
        dataerreur['data']['msg'] = "command Error\n %s"%data['cmd']
        objectxmpp.send_message(mto=message['from'],
                                mbody=json.dumps(dataerreur),
                                mtype='chat')
