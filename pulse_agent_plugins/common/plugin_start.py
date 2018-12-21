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
# file  pulse_xmpp_agent/pluginsmachine/plugin_start.py

import base64
import json
import sys, os
from lib.managepackage import managepackage, search_list_of_deployment_packages
import socket
from lib.grafcetdeploy import grafcet
import logging
import pycurl
import platform
#from lib.utils import save_back_to_deploy, cleanbacktodeploy, simplecommandstr, get_keypub_ssh
from lib.utils import save_back_to_deploy, cleanbacktodeploy, simplecommandstr, isBase64
import copy
import traceback
from sleekxmpp.xmlstream import  JID
import time
logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25

plugin = {"VERSION" : "1.0", "NAME" : "start", "TYPE" : "all"}



def action( objectxmpp, action, sessionid, data, message, dataerreur):
    logger.debug("###################################################")
    logger.debug("call %s from %s"%(plugin, message['from']))
    logger.debug("###################################################")
    if objectxmpp.config.agenttype in ['machine']:
        logger.debug("#################AGENT MACHINE#####################")
        logger.debug("###################################################")

    else:
        logger.debug("###################################################")
        logger.debug("##############AGENT RELAY SERVER###################")
        logger.debug("###################################################")
