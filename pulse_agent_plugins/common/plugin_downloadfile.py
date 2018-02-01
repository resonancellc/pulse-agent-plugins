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

from lib.utils import  simplecommand
import sys
import os
from subprocess import Popen
import shlex
import json
import subprocess
from lib.utils import file_get_contents, file_put_contents
import shutil
import time
import socket

logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25
plugin = { "VERSION" : "1.1", "NAME" : "downloadfile", "TYPE" : "all" }
paramglobal = {"timeupreverssh" : 20 , "portsshmaster" : 22, "filetmpconfigssh" : "/tmp/tmpsshconf", "remoteport" : 22}
def create_path(type ="windows", host="", ipordomain="", path=""):
    """
        warning you must enter a raw string for parameter path
        eg ( a= create_path(host="pulse", ipordomain="192.168.56.103", path=r"C:\Program Files (x86)\Pulse\var\tmp\packages\a170890e-d060-11e7-ade3-0800278dc04d")
    """
    if path == "":
        return ""
    if type == "windows":
        if host != "" and ipordomain != "":
            return "%s@%s:\"\\\"%s\\\"\""%( host,
                                            ipordomain,
                                            path)
        else:
            return "\"\\\"%s\\\"\""%(path)
    elif type == "linux":
        if host != "" and ipordomain != "":
            return "%s@%s:\"%s\""%( host,
                                            ipordomain,
                                            path)
        else:
            return "\"%s\""%(path)

def scpfile(scr, dest, portscr = None, portdest = None):
    if portscr is  None or portdest is None:
        # version fichier de configuration.
        cmdpre = "scp -rp3 -F %s "\
                    "-o IdentityFile=/root/.ssh/id_rsa "\
                    "-o StrictHostKeyChecking=no "\
                    "-o UserKnownHostsFile=/dev/null "\
                    "-o Batchmode=yes "\
                    "-o PasswordAuthentication=no "\
                    "-o ServerAliveInterval=10 "\
                    "-o CheckHostIP=no "\
                    "-o ConnectTimeout=10 "%paramglobal['filetmpconfigssh']
    else :
        cmdpre = "scp -rp3 "\
                    "-o IdentityFile=/root/.ssh/id_rsa "\
                    "-o StrictHostKeyChecking=no "\
                    "-o UserKnownHostsFile=/dev/null "\
                    "-o Batchmode=yes "\
                    "-o PasswordAuthentication=no "\
                    "-o ServerAliveInterval=10 "\
                    "-o CheckHostIP=no "\
                    "-o ConnectTimeout=10 "
    cmdpre =  "%s %s %s"%(cmdpre, scr, dest)
    return cmdpre

def action( objectxmpp, action, sessionid, data, message, dataerreur):
    logging.getLogger().debug("###################################################")
    logging.getLogger().debug("call %s from %s"%(plugin,message['from']))
    logging.getLogger().debug("###################################################")
    print json.dumps(data,indent=4)
    reversessh = False
    localport = 22
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((data['ipmachinepublic'], 22))
    except socket.error:
        localport = randint(49152, 65535)
        reversessh = True
        #send create reverse ssh to machine
    finally:
        sock.close()
    #print json.dumps(data,indent=4)
    #scp file from 2 hosts
    if str(data['osmachine']).startswith('Linux') or str(data['osmachine']).startswith('darwin'):
        source = create_path(type = "linux", host = "root", ipordomain=data['ipmachinepublic'], path = r'%s'%data['path_src_machine'])
    else:
        source = create_path(type = "windows", host = "pulse", ipordomain = data['ipmachinepublic'], path = r'%s'%data['path_src_machine'])
    dest = create_path(type ="linux", host="root", ipordomain=data['ipars'], path=data['path_dest_master'])

    cretefileconfigrescp = "Host %s\nPort %s\nHost %s\nPort %s\n"%(data['ipmaster'], paramglobal['portsshmaster'], data['ipmachinepublic'], localport)
    file_put_contents(paramglobal['filetmpconfigssh'],  cretefileconfigrescp)

    if reversessh == True:
        command = scpfile(source, dest)
    else:
        ##install reverssh

        datareversessh = {
            'action': 'reverse_ssh_on',
            'sessionid': sessionid,
            'data' : {
                    'request' : 'askinfo',
                    'port' : localport,
                    'host' : data['host'],
                    'remoteport' : paramglobal['remoteport'],
                    'reversetype' : 'R',
                    'options' : 'createreversessh'
            },
            'ret' : 0,
            'base64' : False }

        objectxmpp.send_message(mto = message['to'],
                    mbody = json.dumps(datareversessh),
                    mtype = 'chat')
 
        # initialise se cp
        command = scpfile(source, dest, portscr = localport, portdest=paramglobal['portsshmaster'])

        time.sleep(paramglobal['timeupreverssh'])
    print json.dumps(data,indent=4)
    print "----------------------------"
    print "exec command\n %s"%command
    print "----------------------------"
    print "----------------------------"
    z = simplecommand(command)
    print z['result']
    print z['code']
    print "----------------------------"


