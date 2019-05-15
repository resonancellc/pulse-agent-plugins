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
#
# 
# file relay/plugin_downloadfileexpert.py
import logging

from lib.utils import  simplecommand
import os
import json
from lib.utils import file_put_contents
import time
import socket
from random import randint
logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25

plugin = { "VERSION" : "1.4", "NAME" : "downloadfileexpert", "TYPE" : "relayserver" }
paramglobal = {"timeupreverssh" : 30 , "portsshmaster" : 22, "filetmpconfigssh" : "/tmp/tmpsshconf", "remoteport" : 22}
def create_path(type ="windows", host="", ipordomain="", path=""):
    """
        warning you must enter a raw string for parameter path
        eg ( a= create_path(host="pulse", ipordomain="192.168.56.103", path=r"C:\Program Files (x86)\Pulse\var\tmp\packages\a170890e-d060-11e7-ade3-0800278dc04d")
    """
    if path == "":
        return ""
    if type == "windows":
        if host != "" and ipordomain != "":
            if path.endswith("\\"):
                path = path[:-1]
            a= '%s@%s:"\\"%s\\""'%( host,
                                    ipordomain,
                                    path)
            return a
        else:
            return "\"\\\"%s\"\""%(path)
    elif type == "linux":
        if host != "" and ipordomain != "":
            return "%s@%s:\"%s\""%( host,
                                            ipordomain,
                                            path)
        else:
            return "\"%s\""%(path)

def scpfile(scr, dest,  objectxmpp, sessionid, reverbool=False):
    if reverbool:
        # version fichier de configuration.
        cmdpre = "scp -C -rp3 -F %s "\
                    "-o IdentityFile=/root/.ssh/id_rsa "\
                    "-o StrictHostKeyChecking=no "\
                    "-o LogLevel=ERROR "\
                    "-o UserKnownHostsFile=/dev/null "\
                    "-o Batchmode=yes "\
                    "-o PasswordAuthentication=no "\
                    "-o ServerAliveInterval=10 "\
                    "-o CheckHostIP=no "\
                    "-o ConnectTimeout=10 "%paramglobal['filetmpconfigssh']
    else :
        cmdpre = "scp -C -rp3 "\
                    "-o IdentityFile=/root/.ssh/id_rsa "\
                    "-o StrictHostKeyChecking=no "\
                    "-o LogLevel=ERROR "\
                    "-o UserKnownHostsFile=/dev/null "\
                    "-o Batchmode=yes "\
                    "-o PasswordAuthentication=no "\
                    "-o ServerAliveInterval=10 "\
                    "-o CheckHostIP=no "\
                    "-o ConnectTimeout=10 "
    cmdpre =  "%s %s %s"%(cmdpre, scr, dest)
    objectxmpp.xmpplog( 'cmd : ' + cmdpre,
                               type = 'noset',
                               sessionname = sessionid,
                               priority = -1,
                               action = "",
                               who = objectxmpp.boundjid.bare,
                               how = "",
                               why = "",
                               module = "Notify | Download | Transfertfile",
                               date = None ,
                               fromuser = "",
                               touser = "")
    return cmdpre

def action( objectxmpp, action, sessionid, data, message, dataerreur):
    logging.getLogger().debug("###################################################")
    logging.getLogger().debug("call %s from %s"%(plugin,message['from']))
    logging.getLogger().debug("###################################################")
    print json.dumps(data,indent=4)
    #--------------------search si besoin d'un reverse ssh------------------------------------
    #
    logger.debug("Install key ARS in authorized_keys on agent machine")
    body = {'action' : 'installkey',
            'sessionid': sessionid,
            'data' : { 'jidAM' : data['jidmachine']
            }
    }
    objectxmpp.send_message( mto = objectxmpp.boundjid.bare,
                             mbody = json.dumps(body),
                             mtype = 'chat')
    reversessh = False
    localport = 22
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    try:
        sock.connect((data['ipmachine'], 22))
        reversessh = False
        #create file for command scp remote to remote direct connection remote
        cretefileconfigrescp = "Host %s\nPort %s\nHost %s\nPort %s\n"%(data['ipmaster'], paramglobal['portsshmaster'], data['ipmachine'], localport)
    except socket.error:
        localport = randint(49152, 65535)
        reversessh = True
        #send create reverse ssh to machine
        objectxmpp.xmpplog( 'Call Reverse ssh for nat machine %s'% data['hostname'],
                            type = 'noset',
                            sessionname = sessionid,
                            priority = -1,
                            action = "",
                            who = objectxmpp.boundjid.bare,
                            how = "",
                            why = "",
                            module = "Notify | Download | Transfertfile",
                            date = None ,
                            fromuser = "",
                            touser = "")
        cretefileconfigrescp = "Host %s\nPort %s\nHost %s\nPort %s\n"%(data['ipmaster'], paramglobal['portsshmaster'], "localhost", localport)
        datareversessh = {
            'action': 'reverse_ssh_on',
            'sessionid': sessionid,
            'data' : {
                    'request' : 'askinfo',
                    'port' : localport,
                    'host' : data['host'],
                    'remoteport' : paramglobal['remoteport'],
                    'reversetype' : 'R',
                    'options' : 'createreversessh',
                    'persistance' : 'Downloadfile'
            },
            'ret' : 0,
            'base64' : False }
        #self call plugin creation reverse ssh for host data['host']
        objectxmpp.send_message(mto = message['to'],
                                mbody = json.dumps(datareversessh),
                                mtype = 'chat')
        #time for create reverse ssh
        time.sleep(paramglobal['timeupreverssh'])
    finally:
        sock.close()
    file_put_contents(paramglobal['filetmpconfigssh'],  cretefileconfigrescp)
    ##scp file from 2 hosts
    #------------------------------------------------- ssh------------------------------------
    #####
    # Scp les fichiers et repertoires.
    # on commence par les repertoires.

    data['path_src_machine_dir'] = data['path_src_machine_dir'] + data['path_src_machine_file']
    for directory in data['path_src_machine_dir']:
        if reversessh == False:
            if str(data['osmachine']).startswith('Linux'):
                source = create_path(type = "linux", host = "pulseuser", ipordomain=data['ipmachine'], path = r'%s'%directory)
            elif str(data['osmachine']).startswith('darwin'):
                source = create_path(type = "linux", host = "pulseuser", ipordomain=data['ipmachine'], path = r'%s'%directory)
            else:
                source = create_path(type = "windows", host = "pulseuser", ipordomain = data['ipmachine'], path = r'%s'%directory)
        else:
            if str(data['osmachine']).startswith('Linux'):
                source = create_path(type = "linux", host = "pulseuser", ipordomain="localhost", path = r'%s'%directory)
            elif str(data['osmachine']).startswith('darwin'):
                source = create_path(type = "linux", host = "pulseuser", ipordomain="localhost", path = r'%s'%directory)
            else:
                source = create_path(type = "windows", host = "pulseuser", ipordomain = "localhost", path = r'%s'%directory)

        dest = create_path(type ="linux",
                        host="root",
                        ipordomain=data['ipmaster'],
                        path=data['path_dest_master'])
        if reversessh == False:
            command = scpfile(source, dest, objectxmpp, sessionid)
        else:
            # initialise se cp
            command = scpfile(source,
                            dest,
                            objectxmpp,
                            sessionid,
                            reverbool = True)


        print "source %s"%source
        print "dest %s"%dest
        print "command %s"%command

            #time.sleep(paramglobal['timeupreverssh'])


        print json.dumps(data,indent=4)
        print "----------------------------"
        print "exec command\n %s"%command
        print "----------------------------"
        print "----------------------------"
        objectxmpp.xmpplog( 'Copy file %s from machine %s to Master'%( os.path.basename(directory), data['hostname']),
                                    type = 'noset',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Notify | Download | Transfertfile",
                                    date = None ,
                                    fromuser = "",
                                    touser = "")

    
        z = simplecommand(command)
        print z['result']
        print z['code']
        print "----------------------------"

        if z['code'] != 0:
            objectxmpp.xmpplog( 'error Copy file %s from machine %s to Master'%( os.path.basename(directory), data['hostname']),
                                    type = 'noset',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Notify | Download",
                                    date = None ,
                                    fromuser = "",
                                    touser = "")
            objectxmpp.xmpplog( 'error : %s'% z['result'],
                                    type = 'noset',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Notify | Download | Transfertfile",
                                    date = None ,
                                    fromuser = "",
                                    touser = "")
        else:
            objectxmpp.xmpplog( 'success Copy file %s from machine %s to Master'%( os.path.basename(directory), data['hostname']),
                                    type = 'noset',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Notify | Download | Transfertfile",
                                    date = None ,
                                    fromuser = "",
                                    touser = "")
            # chang mod file dest
            tabdest = str(dest).split('"')
            cmd = "ssh %s -o IdentityFile=/root/.ssh/id_rsa "\
                        "-o StrictHostKeyChecking=no "\
                        "-o UserKnownHostsFile=/dev/null "\
                        "-o Batchmode=yes "\
                        "-o PasswordAuthentication=no "\
                        "-o ServerAliveInterval=10 "\
                        "-o CheckHostIP=no "\
                        "-o ConnectTimeout=10 'chmod 777 -R %s'"%(str(tabdest[0][:-1]),os.path.dirname(tabdest[1]))
            objectxmpp.xmpplog( 'cmd : ' + cmd,
                                type = 'noset',
                                sessionname = sessionid,
                                priority = -1,
                                action = "",
                                who = objectxmpp.boundjid.bare,
                                how = "",
                                why = "",
                                module = "Notify | Download | Transfertfile",
                                date = None ,
                                fromuser = "",
                                touser = "")
            z = simplecommand(cmd)
            if z['code'] == 0:
                objectxmpp.xmpplog( 'result transfert : ' + '\n'.join(z['result']),
                                    type = 'noset',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Notify | Download | Transfertfile",
                                    date = None ,
                                    fromuser = "",
                                    touser = "")
                objectxmpp.xmpplog( 'change mode 777 for file %s '%( os.path.basename(directory)),
                                    type = 'noset',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Notify | Download | Transfertfile",
                                    date = None ,
                                    fromuser = "",
                                    touser = "")
            else:
                objectxmpp.xmpplog( 'error change mode 777 for file %s : %s'%( os.path.basename(directory), z['result']),
                                    type = 'noset',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Notify | Download | Transfertfile",
                                    date = None ,
                                    fromuser = "",
                                    touser = "")
