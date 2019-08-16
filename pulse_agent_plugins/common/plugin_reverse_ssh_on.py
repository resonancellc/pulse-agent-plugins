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

# file plugin_reverse_ssh_on.py

import sys
import os
from subprocess import Popen
import shlex
import json
import subprocess
from lib.utils import file_get_contents, file_put_contents, file_put_contents_w_a, simplecommandstr
import shutil
import logging
import traceback

if sys.platform.startswith('win'):
    import win32security
    import ntsecuritycon
    import win32net
    import win32security
    import win32serviceutil
    import win32api

logger = logging.getLogger()
plugin = {"VERSION" : "2.72", "NAME" : "reverse_ssh_on",  "TYPE" : "all"}

def checkresult(result):
    if result['codereturn'] != 0:
        if len (result['result']) == 0:
            result['result'][0]=''
        logger.error("error : %s"%result['result'][-1])
    return result['codereturn'] == 0

def genratekeyforARSreverseSSH():
    logger.debug("############genrate key for ARS reverseSSH ###############")
    if not os.path.isfile(os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh","id_rsa")) or not \
        os.path.isfile(os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh","id_rsa.pub")):
        os.system("useradd reversessh -md /var/lib/pulse2/clients/reversessh -s /bin/rbash")
        if not os.path.isdir(os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh")):
            os.makedirs(os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh"))
        os.system("ssh-keygen -b 2048 -t rsa -f /var/lib/pulse2/clients/reversessh/.ssh/id_rsa -q -N \"\"")
        shutil.copyfile("/var/lib/pulse2/clients/reversessh/.ssh/id_rsa.pub", "/var/lib/pulse2/clients/reversessh/.ssh/authorized_keys")
        os.system("chown -R reversessh: /var/lib/pulse2/clients/reversessh/")
        os.chmod("/var/lib/pulse2/clients/reversessh/.ssh", 0o700)
        os.chmod("/var/lib/pulse2/clients/reversessh/.ssh/authorized_keys", 0o600)

def load_key_ssh_relayserver(private=False, user="reversessh"):
    """
        This function load the sskey
        Args:
            private: Tell if this is the private of the public ssh key

        Returns:
            The content of the sshkey file
    """

    if private == True:
        keyname = "id_rsa"
    else:
        keyname = "id_rsa.pub"
    if user == "root":
        filekey = os.path.join("/", "root", ".ssh", keyname)
    else:
        filekey = os.path.join("/", "var", "lib", "pulse2", "clients", "reversessh", ".ssh", keyname)
    return file_get_contents(filekey)

def runProcess(cmd , shell= False, envoption = os.environ):
    logger.debug("START COMMAND %s"%cmd)
    args = shlex.split(cmd)
    return Popen(args, env=envoption, shell=shell).pid

def install_key_ssh_relayserver(keypriv, private=False):
    """
        This function installs the sshkey
        Args:
            keypriv: The name of the key to copy on the dest machine
            private: Tell if this is the private of the public ssh key
    """
    logger.debug("################## install_key_ssh_relayserver ##############################")
    userprogram = "system"
    if sys.platform.startswith('win'):
        userprogram = win32api.GetUserName().lower()
        # on modifie les droits sur le fichier de key pour reverse ssh dans user
        if userprogram != "system":
            userprogram = "Administrators"
    if private == True:
        keyname = "id_rsa"
        keyperm = 0o600
    else:
        keyname = "id_rsa.pub"
        keyperm = 0o644

    if sys.platform.startswith('linux'):
        if not os.path.isdir(os.path.join(os.path.expanduser('~pulseuser'), ".ssh/")):
            os.makedirs(os.path.join(os.path.expanduser('~pulseuser'), ".ssh/"))
        filekey = os.path.join(os.path.expanduser('~pulseuser'), ".ssh", keyname)
    elif sys.platform.startswith('win'):
        # check if pulse account exists
        try:
            win32net.NetUserGetInfo('','pulse',0)
            filekey = os.path.join(os.environ["ProgramFiles"], "pulse" ,'.ssh', keyname)
            #folderkey = os.path.join(os.environ["ProgramFiles"], "pulse" ,'.ssh')
        except:
            filekey = os.path.join("c:\Users\pulseuser", ".ssh", keyname)
            folderkey = os.path.join("c:\Users\pulseuser", ".ssh")
        logger.debug("filekey  %s"%filekey)
        logger.debug("chang permition to user %s"%userprogram)
        #userfolder, domain, type = win32security.LookupAccountName ("", userprogram)
        #sd = win32security.GetFileSecurity(folderkey, win32security.DACL_SECURITY_INFORMATION)
        #dacl = win32security.ACL ()
        #dacl.AddAccessAllowedAce(win32security.ACL_REVISION, 
                                #ntsecuritycon.FILE_GENERIC_READ | ntsecuritycon.FILE_GENERIC_WRITE,
                                #userfolder)
        #sd.SetSecurityDescriptorDacl(1, dacl, 0)
        #win32security.SetFileSecurity(folderkey, win32security.DACL_SECURITY_INFORMATION, sd)
        if os.path.isfile(filekey):
            user, domain, type = win32security.LookupAccountName ("", userprogram)
            sd = win32security.GetFileSecurity(filekey, win32security.DACL_SECURITY_INFORMATION)
            dacl = win32security.ACL ()
            dacl.AddAccessAllowedAce(win32security.ACL_REVISION, 
                                    ntsecuritycon.FILE_GENERIC_READ | \
                                        ntsecuritycon.FILE_GENERIC_WRITE | \
                                            ntsecuritycon.FILE_ALL_ACCESS,
                                    user)
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(filekey, win32security.DACL_SECURITY_INFORMATION, sd)

    elif sys.platform.startswith('darwin'):
        if not os.path.isdir(os.path.join(os.path.expanduser('~pulseuser'), ".ssh")):
            os.makedirs(os.path.join(os.path.expanduser('~pulseuser'), ".ssh"))
        filekey = os.path.join(os.path.expanduser('~pulseuser'), ".ssh", keyname)
    else:
        return

    if os.path.isfile(filekey):
        try:
            os.remove(filekey)
        except:
            logger.warning("remove %s key impossible"%filekey)

    logger.debug("CREATION DU FICHIER %s"%filekey)
    try:
        file_put_contents(filekey, keypriv)
    except:
        logger.error("\n%s"%(traceback.format_exc()))

    if sys.platform.startswith('win'):
        user, domain, type = win32security.LookupAccountName ("", "SYSTEM")
        sd = win32security.GetFileSecurity(filekey, win32security.DACL_SECURITY_INFORMATION)
        dacl = win32security.ACL ()
        dacl.AddAccessAllowedAce(win32security.ACL_REVISION, 
                                ntsecuritycon.FILE_GENERIC_READ | ntsecuritycon.FILE_GENERIC_WRITE, 
                                user)
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(filekey, win32security.DACL_SECURITY_INFORMATION, sd)
    else:
        os.chmod(filekey, keyperm)

def set_authorized_keys(keypub):
    compte = "pulseuser"
    try:
        if sys.platform.startswith('linux'):
            file_authorized_keys=os.path.join(os.path.expanduser('~pulseuser'), ".ssh", "authorized_keys" )
        elif sys.platform.startswith('win'):
            try:
                win32net.NetUserGetInfo('','pulse',0)
                file_authorized_keys = os.path.join(os.environ["ProgramFiles"],
                                                    "pulse" ,
                                                    '.ssh', 
                                                    "authorized_keys")
                compte = "pulse"
            except:
                file_authorized_keys = os.path.join("c:\Users\pulseuser", ".ssh", "authorized_keys")
            if not os.path.isfile(file_authorized_keys):
                file_put_contents(file_authorized_keys, "\n")
            user, domain, type = win32security.LookupAccountName ("", compte)
            user1, domain, type = win32security.LookupAccountName ("", "sshd")
            user2, domain, type = win32security.LookupAccountName ("", "Administrators")
            user3, domain, type = win32security.LookupAccountName ("", "system")
            sd = win32security.GetFileSecurity(file_authorized_keys,
                                               win32security.DACL_SECURITY_INFORMATION)
            dacl = win32security.ACL ()
            dacl.AddAccessAllowedAce(win32security.ACL_REVISION, 
                                    ntsecuritycon.FILE_GENERIC_READ | ntsecuritycon.FILE_GENERIC_WRITE, 
                                    user)

            sd.SetSecurityDescriptorDacl(1, dacl, 0)


            win32security.SetFileSecurity(file_authorized_keys,
                                          win32security.DACL_SECURITY_INFORMATION, sd)



            dacl.AddAccessAllowedAce(win32security.ACL_REVISION, 
                                    ntsecuritycon.FILE_GENERIC_READ , 
                                    user1)
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(file_authorized_keys, win32security.DACL_SECURITY_INFORMATION, sd)


            dacl.AddAccessAllowedAce(win32security.ACL_REVISION, 
                                    ntsecuritycon.FILE_GENERIC_READ | ntsecuritycon.FILE_GENERIC_WRITE, 
                                    user2)
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(file_authorized_keys, win32security.DACL_SECURITY_INFORMATION, sd)

            dacl.AddAccessAllowedAce(win32security.ACL_REVISION, 
                                    ntsecuritycon.FILE_GENERIC_READ | ntsecuritycon.FILE_ALL_ACCESS, 
                                    user2)
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(file_authorized_keys, win32security.DACL_SECURITY_INFORMATION, sd)

            dacl.AddAccessAllowedAce(win32security.ACL_REVISION,
                                    ntsecuritycon.FILE_GENERIC_READ |  ntsecuritycon.FILE_ALL_ACCESS,
                                    user3)
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(file_authorized_keys, win32security.DACL_SECURITY_INFORMATION, sd)

        elif sys.platform.startswith('darwin'):
            file_authorized_keys = os.path.join(os.path.expanduser('~pulseuser'), ".ssh", "authorized_keys")


        if not os.path.isfile(file_authorized_keys):
            file_put_contents(file_authorized_keys, keypub)
            logger.debug("set authorized_keys key %s"%keypub)
            return True
        else:
            content = file_get_contents(file_authorized_keys)
            if not keypub in content:
                file_put_contents_w_a(file_authorized_keys, keypub, option = "a")
                logger.debug("add key in authorized_keys %s"%keypub)
                return True

    except:
        logger.error("\n%s"%(traceback.format_exc()))
        return False
    return True

def action( objectxmpp, action, sessionid, data, message, dataerreur ):
    logger.debug("###################################################")
    logger.debug("call %s from %s"%(plugin, message['from']))
    logger.debug("%s"%(json.dumps(data, indent=4)))
    logger.debug("###################################################")
    returnmessage = dataerreur
    returnmessage['ret'] = 0
    if objectxmpp.config.agenttype in ['relayserver']:
        #verify key exist
        idkeypub = os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh","id_rsa.pub")
        idkey = os.path.join("/","var","lib","pulse2","clients","reversessh",".ssh","id_rsa")
        if not os.path.isfile(idkey) or not os.path.isfile(idkeypub):
            genratekeyforARSreverseSSH()

        logger.debug("PROCESSING RELAYSERVER")
        if message['from'] == "console":
            if not "request" in data :
                objectxmpp.send_message_agent("console", dataerreur)
                return
            if data['request'] == "askinfo":
                logger.debug( "Processing of request askinfo")
                returnmessage['data'] = data
                returnmessage['data']['fromplugin'] = plugin['NAME']
                returnmessage['data']['typeinfo']  = "info_xmppmachinebyuuid"
                returnmessage['data']['sendother'] = "data@infos@jid"
                returnmessage['data']['sendemettor'] = True
                returnmessage['data']['relayserverip'] = objectxmpp.ipconnection
                returnmessage['data']['key'] = load_key_ssh_relayserver(private=True)
                returnmessage['data']['keypub'] = load_key_ssh_relayserver()
                returnmessage['data']['keypubroot'] = load_key_ssh_relayserver(user="root")
                returnmessage['ret'] = 0
                returnmessage['action'] = "askinfo"
                del returnmessage['data']['request']
                logger.debug("Send master this data")
                logger.debug("%s"%json.dumps(returnmessage, indent = 4))
                objectxmpp.send_message_agent( "master@pulse/MASTER",
                                             returnmessage,
                                             mtype = 'chat')
                objectxmpp.send_message_agent("console", returnmessage)
                return
        if message['from'].bare == message['to'].bare:
            if not "request" in data :
                objectxmpp.send_message_agent(message['to'], dataerreur)
                return
            if data['request'] == "askinfo":
                logger.debug("Processing of request askinfo")
                returnmessage['data'] = data
                returnmessage['data']['fromplugin'] = plugin['NAME']
                returnmessage['data']['typeinfo']  = "info_xmppmachinebyuuid"
                returnmessage['data']['sendother'] = "data@infos@jid"
                returnmessage['data']['sendemettor'] = True
                returnmessage['data']['relayserverip'] = objectxmpp.ipconnection
                returnmessage['data']['key'] = load_key_ssh_relayserver(private=True)
                returnmessage['data']['keypub'] = load_key_ssh_relayserver()
                returnmessage['data']['keypubroot'] = load_key_ssh_relayserver(user="root")
                returnmessage['ret'] = 0
                returnmessage['action'] = "askinfo"
                returnmessage['sessionid'] = sessionid
                del returnmessage['data']['request']
                logger.debug( "Send relayagent this data")
                logger.debug("%s"%json.dumps(returnmessage, indent = 4))
                objectxmpp.send_message_agent("master@pulse/MASTER",
                                              returnmessage,
                                              mtype = 'chat')
                return
    else:
        logger.debug("PROCESSING MACHINE")
        objectxmpp.xmpplog( "REVERSE SSH",
                            type = 'noset',
                            sessionname = sessionid,
                            priority = -1,
                            action = "",
                            who = objectxmpp.boundjid.bare,
                            how = "",
                            why = "",
                            module = "Notify | Packaging | Reversessh",
                            date = None ,
                            fromuser = "",
                            touser = "")

        if data['options'] == "createreversessh":
            install_key_ssh_relayserver(data['key'], private=True)
            install_key_ssh_relayserver(data['keypub'])
            set_authorized_keys(data['keypubroot'])
            if hasattr(objectxmpp.config, 'clients_ssh_port'):
                clientssshport = objectxmpp.config.clients_ssh_port
            else:
                clientssshport = "22"
            try:
                reversetype = data['reversetype']
            except Exception:
                reversetype = 'R'
            try:
                remoteport = data['remoteport']
            except Exception:
                remoteport = clientssshport

            objectxmpp.xmpplog( 'create reverse ssh on machine : %s '\
                                  'type reverse : %s port :%s'%(message['to'], reversetype, data['port']),
                                type = 'noset',
                                sessionname = sessionid,
                                priority = -1,
                                action = "",
                                who = objectxmpp.boundjid.bare,
                                how = "",
                                why = "",
                                module = "Notify | Packaging | Reversessh",
                                date = None ,
                                fromuser = "",
                                touser = "")

            if sys.platform.startswith('linux'):
                filekey = os.path.join(os.path.expanduser('~pulseuser'), ".ssh", "id_rsa")
                dd = """#!/bin/bash
                /usr/bin/ssh -t -t -%s %s:localhost:%s -o StrictHostKeyChecking=no -i "%s" -l reversessh %s&
                """%(reversetype, data['port'], remoteport, filekey, data['relayserverip'])
                reversesshsh = os.path.join(os.path.expanduser('~pulseuser'), "reversessh.sh")
                file_put_contents(reversesshsh,  dd)
                os.chmod(reversesshsh, 0o700)
                args = shlex.split(reversesshsh)
                if not 'persistance' in data:
                    data['persistance'] = "no"
                if 'persistance' in data and data['persistance'].lower() != "no":
                    if data['persistance'] in objectxmpp.reversesshmanage:
                        logger.info("suppression reversessh %s"%str(objectxmpp.reversesshmanage[data['persistance']]))
                        cmd = "kill -9 %s"%str(objectxmpp.reversesshmanage[data['persistance']])
                        logger.info(cmd)
                        simplecommandstr(cmd)
                        objectxmpp.xmpplog( "suppression reversessh %s"%str(objectxmpp.reversesshmanage[data['persistance']]),
                                        type = 'noset',
                                        sessionname = sessionid,
                                        priority = -1,
                                        action = "",
                                        who = objectxmpp.boundjid.bare,
                                        how = "",
                                        why = "",
                                        module = "Notify | Reversessh",
                                        date = None ,
                                        fromuser = "",
                                        touser = "")
                result = subprocess.Popen(args)
                if 'persistance' in data and data['persistance'].lower() != "no":
                    objectxmpp.reversesshmanage[data['persistance']] = str(result.pid)
                else:
                    objectxmpp.reversesshmanage['other'] = str(result.pid)
                logger.info("creation reverse ssh pid = %s"% str(result.pid))
                objectxmpp.xmpplog( 'create reverse ssh on machine : %s '\
                                  'type reverse : %s port :%s'%(message['to'], reversetype, data['port']),
                                type = 'noset',
                                sessionname = sessionid,
                                priority = -1,
                                action = "",
                                who = objectxmpp.boundjid.bare,
                                how = "",
                                why = "",
                                module = "Notify | Packaging | Reversessh",
                                date = None ,
                                fromuser = "",
                                touser = "")
            elif sys.platform.startswith('win'):
                ################# win reverse #################
                try:
                    win32net.NetUserGetInfo('','pulse',0)
                    filekey = os.path.join(os.environ["ProgramFiles"], 'pulse', ".ssh", "id_rsa")
                except:
                    filekey = os.path.join("c:\Users\pulseuser", ".ssh", "id_rsa")
                # il faut adapter les droit du fichier idrsa suivant si console administrator ou system.

                userprogram = win32api.GetUserName().lower()
                # on modifie les droits sur le fichier de key pour reverse ssh dans user
                if userprogram != "system":
                    userprogram = "Administrators"

                user, domain, type = win32security.LookupAccountName ("", userprogram)
                sd = win32security.GetFileSecurity(filekey,
                                                win32security.DACL_SECURITY_INFORMATION)
                dacl = win32security.ACL ()
                dacl.AddAccessAllowedAce(win32security.ACL_REVISION, 
                                         ntsecuritycon.FILE_GENERIC_READ | ntsecuritycon.FILE_GENERIC_WRITE, 
                                         user)
                sd.SetSecurityDescriptorDacl(1, dacl, 0)


                win32security.SetFileSecurity(filekey,
                                              win32security.DACL_SECURITY_INFORMATION, sd)

                os_platform = os.environ['PROCESSOR_ARCHITECTURE']
                try:
                    os_platform = os.environ["PROCESSOR_ARCHITEW6432"] # Will raise exception if x86 arch
                except KeyError:
                    pass
                sshexec =  os.path.join(os.environ["ProgramFiles"], "OpenSSH", "ssh.exe")
                reversesshbat = os.path.join(os.environ["ProgramFiles"], "Pulse", "bin", "reversessh.bat")

                linecmd=[]
                cmd ="""\\"%s\\" -t -t -%s %s:localhost:%s -o StrictHostKeyChecking=no -i \\"%s\\" -l reversessh %s"""%( sshexec,
                                                                                                                     reversetype,
                                                                                                                     data['port'],
                                                                                                                     remoteport,
                                                                                                                     filekey,
                                                                                                                     data['relayserverip'])

                linecmd.append( """@echo off""")
                linecmd.append( """for /f "tokens=2 delims==; " %%%%a in (' wmic process call create "%s" ^| find "ProcessId" ') do set "$PID=%%%%a" """%cmd)
                linecmd.append( """echo %$PID%""")
                linecmd.append( """echo %$PID% > C:\\"Program Files"\\Pulse\\bin\\%$PID%.pid""")
                dd = '\r\n'.join(linecmd)



                #dd = """"%s" -t -t -%s %s:localhost:%s -o StrictHostKeyChecking=no -i "%s" -l reversessh %s
                #"""%(sshexec, reversetype, data['port'], remoteport, filekey, data['relayserverip'])

                if not os.path.exists(os.path.join(os.environ["ProgramFiles"], "Pulse", "bin")):
                    os.makedirs(os.path.join(os.environ["ProgramFiles"], "Pulse", "bin"))
                file_put_contents(reversesshbat,  dd)
                if not 'persistance' in data:
                    data['persistance'] = "no"
                
                
                

                if 'persistance' in data and data['persistance'].lower() != "no":
                    ###autre piste.
                    ###### voir cela powershell.exe "Stop-Process -Force (Get-NetTCPConnection -LocalPort 22).OwningProcess"
                    #### cmd = 'wmic path win32_process Where "Commandline like \'%reversessh%\'" Call Terminate'
                    if data['persistance'] in objectxmpp.reversesshmanage:
                        logger.info("suppression reversessh %s"%str(objectxmpp.reversesshmanage[data['persistance']]))
                        cmd = "taskkill /F /PID %s"%str(objectxmpp.reversesshmanage[data['persistance']])
                        logger.info(cmd)
                        simplecommandstr(cmd)
                        objectxmpp.xmpplog( "suppression reversessh %s"%str(objectxmpp.reversesshmanage[data['persistance']]),
                                        type = 'noset',
                                        sessionname = sessionid,
                                        priority = -1,
                                        action = "",
                                        who = objectxmpp.boundjid.bare,
                                        how = "",
                                        why = "",
                                        module = "Notify | Reversessh",
                                        date = None ,
                                        fromuser = "",
                                        touser = "")
                    # clear tout les reverse ssh
                    #searchreversesshprocess = os.path.join(os.environ["ProgramFiles"], "Pulse", "bin")
                    #for f in [ os.path.join(os.environ["ProgramFiles"], "Pulse", "bin", x) \
                                #for x in os.listdir(searchreversesshprocess) if x[-4:]== ".pid"]:
                        #pid= file_get_contents(f).strip(" \n\r\t")
                        #cmd = "taskkill /F /PID %s"%str(pid)
                        #logger.info(cmd)
                        #simplecommand(cmd)
                        #os.remove(f)

                result = subprocess.Popen(reversesshbat)
                #pidfile = os.path.join(os.environ["ProgramFiles"],
                                       #"Pulse", 
                                       #"bin", 
                                       #"%s.pid"%str(result.pid))
                #file_put_contents(pidfile, str(result.pid))
                # le pid est celui du .bat pas celui de windows a revoir pour result.pid
                if 'persistance' in data and data['persistance'].lower() != "no":
                    objectxmpp.reversesshmanage[data['persistance']] = str(result.pid)
                else:
                    objectxmpp.reversesshmanage['other'] = str(result.pid)
                logger.info("creation reverse ssh pid = %s"% str(result.pid))
                objectxmpp.xmpplog( 'create reverse ssh on machine : %s '\
                                  'type reverse : %s port :%s'%(message['to'], reversetype, data['port']),
                                type = 'noset',
                                sessionname = sessionid,
                                priority = -1,
                                action = "",
                                who = objectxmpp.boundjid.bare,
                                how = "",
                                why = "",
                                module = "Notify | Packaging | Reversessh",
                                date = None ,
                                fromuser = "",
                                touser = "")

            elif sys.platform.startswith('darwin'):
                filekey = os.path.join(os.path.expanduser('~pulseuser'), ".ssh", "id_rsa")
                dd = """#!/bin/bash
                /usr/bin/ssh -t -t -%s %s:localhost:%s -o StrictHostKeyChecking=no -i "%s" -l reversessh %s&
                """%(reversetype, data['port'], remoteport, filekey, data['relayserverip'])
                reversesshsh = os.path.join(os.path.expanduser('~pulseuser'), "reversessh.sh")
                file_put_contents(reversesshsh,  dd)
                os.chmod(reversesshsh, 0o700)
                args = shlex.split(reversesshsh)
                if not 'persistance' in data:
                    data['persistance'] = "no"
                if 'persistance' in data and data['persistance'].lower() != "no":
                    if data['persistance'] in objectxmpp.reversesshmanage:
                        logger.info("suppression reversessh %s"%str(objectxmpp.reversesshmanage[data['persistance']]))
                        cmd = "kill -9 %s"%str(objectxmpp.reversesshmanage[data['persistance']])
                        logger.info(cmd)
                        simplecommandstr(cmd)
                        objectxmpp.xmpplog( "suppression reversessh %s"%str(objectxmpp.reversesshmanage[data['persistance']]),
                                        type = 'noset',
                                        sessionname = sessionid,
                                        priority = -1,
                                        action = "",
                                        who = objectxmpp.boundjid.bare,
                                        how = "",
                                        why = "",
                                        module = "Notify | Reversessh",
                                        date = None ,
                                        fromuser = "",
                                        touser = "")
                result = subprocess.Popen(args)
                if 'persistance' in data and data['persistance'].lower() != "no":
                    objectxmpp.reversesshmanage[data['persistance']] = str(result.pid)
                else:
                    objectxmpp.reversesshmanage['other'] = str(result.pid)
                    data['persistance'] = "no"
                logger.info("creation reverse ssh pid = %s"% str(result.pid))
                objectxmpp.xmpplog(  "creation reverse ssh pid = %s"% str(result.pid),
                                    type = 'noset',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Notify | Reversessh",
                                    date = None ,
                                    fromuser = "",
                                    touser = "")
            else:
                logger.warning("os not supported in plugin%s"%sys.platform)
        elif data['options'] == "stopreversessh":
            if sys.platform.startswith('win'):
                ### voir cela powershell.exe "Stop-Process -Force (Get-NetTCPConnection -LocalPort 22).OwningProcess"

                cmd = 'wmic path win32_process Where "Commandline like \'%reversessh%\'" Call Terminate'
                subprocess.Popen(cmd)
            else:
                os.system("lpid=$(ps aux | grep reversessh | grep -v grep | awk '{print $2}');kill -9 $lpid")
                objectxmpp.reversessh = None

        returnmessage = dataerreur
        returnmessage['data'] = data
        returnmessage['ret'] = 0
