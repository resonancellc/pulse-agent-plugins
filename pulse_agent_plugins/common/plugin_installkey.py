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

import sys
import os
import logging
from lib.utils import file_get_contents, file_put_contents_w_a, simplecommand, encode_strconsole, decode_strconsole, file_put_contents
import json
import uuid

logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25

plugin = { "VERSION" : "1.45", "NAME" : "installkey", "TYPE" : "all" }

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
            import pwd
            import grp
            #verify compte pulse exist
            try:
                uid = pwd.getpwnam("pulseuser").pw_uid
                gid = grp.getgrnam("pulseuser").gr_gid
                gidroot = grp.getgrnam("root").gr_gid
            except:
                #le compte n'existe pas
                result = simplecommand(encode_strconsole("adduser --system --group --home /var/lib/pulse2 --shell /bin/rbash --disabled-password pulseuser"))
            uid = pwd.getpwnam("pulseuser").pw_uid
            gid = grp.getgrnam("pulseuser").gr_gid
            gidroot = grp.getgrnam("root").gr_gid
            authorized_keys_path = os.path.join(os.path.expanduser('~pulseuser'), '.ssh', 'authorized_keys')
            if not os.path.isdir(os.path.dirname(authorized_keys_path)):
                os.makedirs(os.path.dirname(authorized_keys_path), 0700)
            if not os.path.isfile(authorized_keys_path):
                file_put_contents(authorized_keys_path,"")
            os.chown(os.path.dirname(authorized_keys_path), uid, gid)
            os.chown(authorized_keys_path, uid, gid)
            os.chown(authorized_keys_path, uid, gid)
            packagepath = os.path.join(os.path.expanduser('~pulseuser'), 'packages')
            if not os.path.isfile(packagepath):
                os.makedirs(packagepath, 0764)
            os.chown(packagepath, uid, gidroot)
            os.chmod(os.path.dirname(authorized_keys_path), 0700)
            os.chmod(authorized_keys_path, 0644)
            os.chmod(packagepath, 0764)
            result = simplecommand(encode_strconsole("chown -R pulseuser: '/var/lib/pulse'"))
        elif sys.platform.startswith('win'):
            import win32net
            # check if pulse account exists
            try:
                win32net.NetUserGetInfo('','pulse',0)
            except:
                # pulse account doesn't exist
                pulseuserpassword = uuid.uuid4().hex
                pulseuserhome = os.path.join(os.environ["ProgramFiles"], 'Pulse')
                result = simplecommand(encode_strconsole('net user "pulse" "%s" /ADD /COMMENT:"Pulse user with admin rights on the system" /PROFILEPATH:"%s"' % (pulseuserpassword, pulseuserhome)))
                logging.getLogger().debug("Creation of pulse user: %s" %result)
            authorized_keys_path = os.path.join(os.environ["ProgramFiles"], 'Pulse', '.ssh','authorized_keys' )
            if not os.path.isdir(os.path.dirname(authorized_keys_path)):
                os.makedirs(os.path.dirname(authorized_keys_path), 0700)
            if not os.path.isfile(authorized_keys_path):
                file_put_contents(authorized_keys_path,"")
            os.chdir(os.path.join(os.environ["ProgramFiles"], 'OpenSSH'))
            result = simplecommand(encode_strconsole('powershell -ExecutionPolicy Bypass -Command ". .\FixHostFilePermissions.ps1 -Confirm:$false"'))
            logging.getLogger().debug("Reset of permissions on ssh keys and folders: %s" %result)
        elif sys.platform.startswith('darwin'):
            authorized_keys_path = os.path.join(os.path.join(os.path.expanduser('~pulse'), '.ssh', 'authorized_keys') )
        else:
            return

        authorized_keys_content = file_get_contents(authorized_keys_path)
        if not data['key'] in authorized_keys_content:
            #add en append la key dans le fichier
            file_put_contents_w_a( authorized_keys_path, data['key'], "a" )
            logging.getLogger().debug("install key ARS [%s]"%message['from'])
            if sessionid.startswith("command"):
                notify = "Notify | QuickAction"
            else:
                notify = "Deployment | Cluster | Notify"

            objectxmpp.xmpplog( 'INSTALL key ARS %s on AM %s'%(message['from'], objectxmpp.boundjid.bare),
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
