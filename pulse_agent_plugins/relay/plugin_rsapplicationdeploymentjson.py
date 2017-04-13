# -*- coding: utf-8 -*-
#
# (c) 2016-2017 siveo, http://www.siveo.net
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

import json
import sys
import os
from lib.managepackage import managepackage

from lib.grafcetdeploy import grafcet
import pprint
import logging
import pycurl

import platform
from lib.utils import shellcommandtimeout

logger = logging.getLogger()

plugin = {"VERSION" : "1.0", "NAME" : "rsapplicationdeploymentjson", "TYPE" : "relayserver"}



def action(objectxmpp, action, sessionid, data, message, dataerreur):
    logging.getLogger().debug("RECV data message %s\n###############\n"%json.dumps(data, indent=4))

    datasend = {
                    'action': action,
                    'sessionid': sessionid,
                    'data' : {},
                    'ret' : 0,
                    'base64' : False
                }

    logging.getLogger().debug("#################RELAY SERVER#####################")
    logging.getLogger().debug("##############demande pacquage %s ##############"%(data['deploy']))
    logging.getLogger().debug("#############################################")

    #envoy descripteur

    descriptor =  managepackage.getdescripteurpathpackageuuid(data['deploy'])

    if descriptor is not None:
        datasend['action'] = "applicationdeploymentjson"
        datasend['data'] = { "descriptor" : descriptor}
        datasend['data'] ['path'] = os.path.join(managepackage.packagedir(), data['deploy'])
        datasend['data'] ['packagefile'] = os.listdir(datasend['data']['path'])
        datasend['data'] ['Dtypequery'] =  "TQ"
        datasend['data'] ['Devent'] = "STARDEPLOY"
        datasend['data'] ['name'] = managepackage.getNamepathpackageuuid(data['deploy'])
        print json.dumps(datasend, indent=4)
        objectxmpp.send_message(   mto=message['from'],
                                            mbody=json.dumps(datasend),
                                            mtype='chat')
