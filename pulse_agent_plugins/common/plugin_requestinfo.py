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


# This plugin needs to call back the plugin that made the request to return the result

import json
import sys
from lib.managepackage import managepackage

import logging


logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25
plugin = { "VERSION" : "1.0", "NAME" : "requestinfo", "TYPE" : "all" }

def action( objectxmpp, action, sessionid, data, message, dataerreur):
    result = {
                'action': "result%s"%action,
                'sessionid': sessionid,
                'data' : {},
                'ret' : 0,
                'base64' : False }
    # This plugin needs to call back the plugin that made the request to return the result
    if 'actionasker' in data:
        result['action'] = data['actionasker']

    # Can tell the requester where the call was received
    if 'step' in data:
        result['step'] = data['step']
 
    if 'actiontype' in data:
        result['actiontype'] = data['actiontype']

    #reply data
    if 'dataask' in data:
        for informations in data['dataask']:
            if informations == "folders_packages":
                if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
                    result['data']["folders_packages"] = managepackage.packagedir() + "/"
                elif sys.platform.startswith('win'):
                    result['data']["folders_packages"] = managepackage.packagedir() + "\\"

    if 'sender' in data:
        for senderagent in ['data']["sender"]:
            objectxmpp.send_message( mto=senderagent,
                             mbody=json.dumps(result),
                             mtype='chat')

    #message 
    objectxmpp.send_message( mto=message['from'],
                             mbody=json.dumps(result),
                             mtype='chat')
