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
# file common/plugin_installkey.py

import sys, os
import logging
from lib.utils import file_get_contents, file_put_contents_w_a

logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25

plugin = { "VERSION" : "1.1", "NAME" : "installkey", "TYPE" : "all" }

def action( objectxmpp, action, sessionid, data, message, dataerreur):
    logging.getLogger().debug("###################################################")
    logging.getLogger().debug("call %s from %s"%(plugin, message['from']))
    logging.getLogger().debug("###################################################")
    dataerreur = {  "action" : "result" + action,
                    "data" : { "msg" : "error plugin : " + action
                    },
                    'sessionid' : sessionid,
                    'ret' : 255,
                    'base64' : False
    }

    if objectxmpp.config.agenttype in ['machine']:
        logging.getLogger().debug("#######################################################")
        logging.getLogger().debug("##############AGENT INSTALL KEY MACHINE################")
        logging.getLogger().debug("#######################################################")

        if not 'key' in data:
            objectxmpp.send_message_agent(message['from'], dataerreur, mtype = 'chat')
            return
        #install keypub on AM
        if sys.platform.startswith('linux'):
            authorized_keys_file = file_get_contents(os.path.join('/', 'var', 'lib', 'pulse2', '.ssh', 'authorized_keys'))
        elif sys.platform.startswith('win'):
            authorized_keys_file = os.path.join(os.environ["ProgramFiles"], 'Pulse', '.ssh','authorized_keys' )
        elif sys.platform.startswith('darwin'):
            authorized_keys_file = file_get_contents(os.path.join('/', 'var', 'lib', 'pulse2', '.ssh', 'authorized_keys'))
        else:
            return

        if not data['key'] in authorized_keys_file:
            #add en append la key dans le fichier
            file_put_contents_w_a( os.path.join('/', 'var', 'lib', 'pulse2', '.ssh', 'authorized_keys'), data['key'], "a" )
            logging.getLogger().debug("install key ARS [%s]"%message['from'])
            if sessionid.startswith("command"):
                notify = "Notify | QuickAction"
            else:
                notify = "Deployment | Cluster | Notify"
            objectxmpp.xmpplog( 'INSTALL key ARS %s on AM %s : %s'%(message['from'], objectxmpp.boundjid.bare),
                                type = 'deploy',
                                sessionname = sessionid,
                                priority = -1,
                                action = "",
                                who = objectxmpp.boundjid.bare,
                                how = "",
                                why = "",
                                module = notify,
                                date = None ,
                                fromuser = "",
                                touser = "")
        else:
            logging.getLogger().warning("key ARS [%s] : is already installed."%message['from'])
            #if on veut que ce soit notifier dans le deployement
            #if sessionid.startswith("command"):
                #notify = "Notify | QuickAction"
            #else:
                #notify = "Deployment | Cluster | Notify"
            #objectxmpp.xmpplog("key ARS [%s] : is already installed on AM %s."%(message['from'], objectxmpp.boundjid.bare),
                                    #type = 'deploy',
                                    #sessionname = sessionid,
                                    #priority = -1,
                                    #action = "",
                                    #who = objectxmpp.boundjid.bare,
                                    #how = "",
                                    #why = "",
                                    #module = notify,
                                    #date = None ,
                                    #fromuser = "",
                                    #touser = "")
    else:
        logging.getLogger().debug("#######################################################")
        logging.getLogger().debug("##############AGENT RELAY SERVER KEY MACHINE###########")
        logging.getLogger().debug("#######################################################")
        # send keupub ARM TO AM
        # ARM ONLY DEBIAN
        # lit la key Public
        key = ""
        key = file_get_contents(os.path.join('/', 'root', '.ssh', 'id_rsa.pub'))
        if key == "":
            dataerreur['data']['msg'] = "%s : KEY ARM MISSING"%dataerreur['data']['msg']
            objectxmpp.send_message_agent(message['from'], dataerreur, mtype = 'chat')
            return

        print key
        if not 'jidAM' in data:
            dataerreur['data']['msg'] = "%s JID AM MISSING"%dataerreur['data']['msg']
            objectxmpp.send_message_agent(message['from'], dataerreur, mtype = 'chat')
            return

        datasend = {  "action" : action,
                    "data" : { "key" : key },
                    'sessionid' : sessionid,
                    'ret' : 255,
                    'base64' : False
        }

        objectxmpp.send_message_agent( data['jidAM'], datasend, mtype = 'chat')
