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

import sys
import os
from subprocess import Popen
import shlex
import json
import subprocess
from lib.utils import file_get_contents, file_put_contents
import shutil
import logging

def checkresult(result):
    if result['codereturn'] != 0:
        if len (result['result']) == 0:
            result['result'][0]=''
        logging.getLogger().error("error : %s"%result['result'][-1])
    return result['codereturn'] == 0

def genratekeyforARSreverseSSH():
    print "############genratekeyforARSreverseSSH###############"
    if not os.path.isfile(os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh","id_rsa")) or not \
        os.path.isfile(os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh","id_rsa.pub")):
        os.system("useradd reversessh -md /var/lib/pulse2/clients/reversessh -s /bin/rbash")
        os.makedirs("/var/lib/pulse2/clients/reversessh/.ssh/")
        os.system("ssh-keygen -b 2048 -t rsa -f /var/lib/pulse2/clients/reversessh/.ssh/id_rsa -q -N \"\"")
        shutil.copyfile("/var/lib/pulse2/clients/reversessh/.ssh/id_rsa.pub", "/var/lib/pulse2/clients/reversessh/.ssh/authorized_keys")
        os.system("chown -R reversessh: /var/lib/pulse2/clients/reversessh/")
        os.chmod("/var/lib/pulse2/clients/reversessh/.ssh", 0o700)
        os.chmod("/var/lib/pulse2/clients/reversessh/.ssh/authorized_keys", 0o600)

def load_key_ssh_relayserver():
    filekey = os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh","id_rsa")
    return file_get_contents(filekey)

def load_keypub_ssh_relayserver():
    filekey = os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh","id_rsa.pub")
    return file_get_contents(filekey)

def runProcess(cmd , shell= False, envoption = os.environ):
    print "LANCE COMMANDE %s"%cmd
    args = shlex.split(cmd)
    return Popen(args, env=envoption, shell=shell).pid

def install_keypriv_ssh_relayserver(keypriv):
    if sys.platform.startswith('linux'):
        if not os.path.isdir(os.path.join(os.path.expanduser('~reversessh'), ".ssh/")):
            os.makedirs(os.path.join(os.path.expanduser('~reversessh'), ".ssh/"))
        filekey = os.path.join("/","home","reversessh",".ssh", "id_rsa")
    elif sys.platform.startswith('win'):
        filekey = os.path.join(os.environ["ProgramFiles"], "Pulse", ".ssh", "id_rsa")
    elif sys.platform.startswith('darwin'):
        os.makedirs("/Users/reversessh/.ssh")
        filekey = os.path.join("/","Users","reversessh",".ssh", "id_rsa")
    else:
        return
    file_put_contents(filekey,  keypriv)
    if sys.platform.startswith('win'):
        import win32security
        import ntsecuritycon
        user, domain, type = win32security.LookupAccountName ("", "System")
        sd = win32security.GetFileSecurity(filekey, win32security.DACL_SECURITY_INFORMATION)
        dacl = win32security.ACL ()
        dacl.AddAccessAllowedAce(win32security.ACL_REVISION, ntsecuritycon.FILE_GENERIC_READ | ntsecuritycon.FILE_GENERIC_WRITE, user)
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(filekey, win32security.DACL_SECURITY_INFORMATION, sd)
    else:
        os.chmod(filekey, 0o600)

def install_keypub_ssh_relayserver(keypub):
    if sys.platform.startswith('linux'):
        if not os.path.isdir(os.path.join(os.path.expanduser('~reversessh'), ".ssh/")):
            os.makedirs(os.path.join(os.path.expanduser('~reversessh'), ".ssh/"))
        filekey = os.path.join("/","home","reversessh",".ssh", "id_rsa.pub")
    elif sys.platform.startswith('win'):
        filekey = os.path.join(os.environ["ProgramFiles"], "Pulse", ".ssh", "id_rsa.pub")
    elif sys.platform.startswith('darwin'):
        os.makedirs("/Users/reversessh/.ssh")
        filekey = os.path.join("/","Users","reversessh",".ssh", "id_rsa.pub")
    else:
        return
    file_put_contents(filekey,  keypub)
    if sys.platform.startswith('win'):
        import win32security
        import ntsecuritycon
        user, domain, type = win32security.LookupAccountName ("", "System")
        sd = win32security.GetFileSecurity(filekey, win32security.DACL_SECURITY_INFORMATION)
        dacl = win32security.ACL ()
        dacl.AddAccessAllowedAce(win32security.ACL_REVISION, ntsecuritycon.FILE_GENERIC_READ | ntsecuritycon.FILE_GENERIC_WRITE, user)
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(filekey, win32security.DACL_SECURITY_INFORMATION, sd)
    else:
        os.chmod(filekey, 0o644)

plugin = {"VERSION" : "1.5", "NAME" : "reverse_ssh_on",  "TYPE" : "all"}


def action( objetxmpp, action, sessionid, data, message, dataerreur ):
    print plugin
    print "############data in############### %s"%message['from']
    print json.dumps(data, indent=4)
    print "############data in###############"
    returnmessage = dataerreur
    returnmessage['ret'] = 0
    if objetxmpp.config.agenttype in ['relayserver']:
        #verify key exist
        if not os.path.isfile(os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh","id_rsa")) or not \
            os.path.isfile(os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh","id_rsa.pub")):
            genratekeyforARSreverseSSH()
        print "PROCESSING RELAYSERVER"
        if message['from'] == "console":
            if not "request" in data :
                objetxmpp.send_message_agent("console", dataerreur)
                return
            print message['from']
            print "master@pulse/MASTER"
            if data['request'] == "askinfo":
                print "Processing of request askinfo"
                returnmessage['data'] = data
                returnmessage['data']['fromplugin'] = plugin['NAME']
                returnmessage['data']['typeinfo']  = "info_xmppmachinebyuuid"
                returnmessage['data']['sendother'] = "data@infos@jid"
                returnmessage['data']['sendemettor'] = True
                returnmessage['data']['relayserverip'] = objetxmpp.ipconnection
                returnmessage['data']['key'] = load_key_ssh_relayserver()
                returnmessage['data']['keypub'] = load_keypub_ssh_relayserver()
                returnmessage['ret'] = 0
                returnmessage['action'] = "askinfo"
                del returnmessage['data']['request']
                print "Send master this data"
                print json.dumps(returnmessage, indent = 4)
                objetxmpp.send_message_agent( "master@pulse/MASTER",
                                             returnmessage,
                                             mtype = 'chat')
                objetxmpp.send_message_agent("console", returnmessage)
                return
    else:
        print "PROCESSING MACHINE \n%s\n"%json.dumps(data, indent = 4)

        if data['options'] == "createreversessh":
            install_keypriv_ssh_relayserver(data['key'])
            install_keypub_ssh_relayserver(data['keypub'])
            try:
                reversetype = data['reversetype']
            except AttributeError:
                reversetype = 'R'
            try:
                remoteport = data['remoteport']
            except AttributeError:
                remoteport = '22'
            if objetxmpp.reversessh is not None:
                print "WARNING reverse ssh exists"
            if sys.platform.startswith('linux'):
                dd = """#!/bin/bash
                /usr/bin/ssh -t -t -%s %s:localhost:%s -o StrictHostKeyChecking=no -i "/home/reversessh/.ssh/id_rsa" -l reversessh %s&
                """%(reversetype, data['port'], remoteport, data['relayserverip'])
                file_put_contents("/home/reversessh/reversessh.sh",  dd)
                os.system("chmod  u+x /home/reversessh/reversessh.sh")
                args = shlex.split("/home/reversessh/reversessh.sh")
                objetxmpp.reversessh = subprocess.Popen(args)
            elif sys.platform.startswith('win'):
                filekey = os.path.join(os.environ["ProgramFiles"], "Pulse", ".ssh", "id_rsa")
                sshexec =  os.path.join(os.environ["ProgramW6432"], "OpenSSH", "ssh.exe")
                reversesshbat = os.path.join(os.environ["ProgramFiles"], "Pulse", "bin", "reversessh.bat")
                dd = """"%s" -t -t -%s %s:localhost:%s -o StrictHostKeyChecking=no -i "%s" -l reversessh %s
                """%(sshexec, reversetype, data['port'], remoteport, filekey, data['relayserverip'])
                if not os.path.exists(os.path.join(os.environ["ProgramFiles"], "Pulse", "bin")):
                    os.makedirs(os.path.join(os.environ["ProgramFiles"], "Pulse", "bin"))
                file_put_contents(reversesshbat,  dd)
                objetxmpp.reversessh = subprocess.Popen(reversesshbat)
            elif sys.platform.startswith('darwin'):
                dd = """#!/bin/bash
                /usr/bin/ssh -t -t -%s %s:localhost:%s -o StrictHostKeyChecking=no -i "/home/reversessh/.ssh/id_rsa" -l reversessh %s&
                """%(reversetype, data['port'], remoteport, data['relayserverip'])
                file_put_contents("/home/reversessh/reversessh.sh",  dd)
                os.system("chmod  u+x /home/reversessh/reversessh.sh")
                args = shlex.split("/home/reversessh/reversessh.sh")
                objetxmpp.reversessh = subprocess.Popen(args)
            else:
                dd=""
        elif data['options'] == "stopreversessh":
            if sys.platform.startswith('win'):
                cmd = 'wmic path win32_process Where "Commandline like \'%reversessh%\'" Call Terminate'
                proc = subprocess.Popen(cmd)
            else:
                os.system("lpid=$(ps aux | grep reversessh | grep -v grep | awk '{print $2}');kill -9 $lpid")
                objetxmpp.reversessh = None

        returnmessage = dataerreur
        returnmessage['data'] = data
        returnmessage['ret'] = 0

        print json.dumps(returnmessage, indent = 4)
        print "################################################################################"


        ##objetxmpp.send_message_agent("console", returnmessage)
