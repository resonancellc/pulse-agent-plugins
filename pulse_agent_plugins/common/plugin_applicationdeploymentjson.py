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
# file  plugin_applicationdeploymentjson.py

import base64
import json
import sys, os
from lib.managepackage import managepackage, search_list_of_deployment_packages
import socket
from lib.grafcetdeploy import grafcet
import logging
import pycurl
import platform
from random import randint
from lib.utils import save_back_to_deploy, cleanbacktodeploy, simplecommandstr,\
    simplecommand, encode_strconsole
import copy
import traceback
from sleekxmpp.xmlstream import  JID
import time
from subprocess import STDOUT, check_output

if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
    import grp
    import pwd
elif sys.platform.startswith('win'):
    pass


plugin = {"VERSION" : "3.393", "NAME" : "applicationdeploymentjson", "VERSIONAGENT" : "2.0.0", "TYPE" : "all"}

Globaldata = { 'port_local' : 22 }
logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25
"""
Plugin for deploying a package
"""
def maximum(x,y) :
    if x>y :
        return(x)
    else :
        return(y)

def get_free_tcp_port():
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    addr, port = tcp.getsockname()
    tcp.close()
    return port

def clear_chargeapparente(objectxmpp):
    timechargeapparente = 3 #duree de la valeur de la charge apparente.
    q=time.time()
    for ars in objectxmpp.charge_apparente_cluster.copy():
        if (q - objectxmpp.charge_apparente_cluster[ars]['time']) >=timechargeapparente:
            # il faut remettre la charge apparente a time.time
            objectxmpp.charge_apparente_cluster[ars]['time'] = q
            objectxmpp.charge_apparente_cluster[ars]['charge']=0

def add_chargeapparente(objectxmpp, ars):
    #create structure if not exist
    if not ars in objectxmpp.charge_apparente_cluster:
        objectxmpp.charge_apparente_cluster[ars] = {}
        objectxmpp.charge_apparente_cluster[ars]['charge'] = 0
        objectxmpp.charge_apparente_cluster[ars]['time'] = time.time()

def changown_dir_of_file(dest, nameuser = None):
    if nameuser is None:
    	nameuser = "pulseuser"

    dest = os.path.dirname(dest)
    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        try:
            uid = pwd.getpwnam(nameuser).pw_uid
            gid = grp.getgrnam(nameuser).gr_gid
            os.chown(dest, uid, gid)
            for dirpath, dirnames, filenames in os.walk(dest):
                for dname in dirnames:
                    os.chown(os.path.join(dirpath, dname), uid, gid)
                for fname in filenames:
                    os.chown(os.path.join(dirpath, fname), uid, gid)
        except Exception as e:
            logger.error("%s changown_dir_of_file : %s"%(dest, str(e) ))
    elif sys.platform.startswith('win'):
        try:
            check_output(["icacls",
                          encode_strconsole(dest),
                          "/setowner",
                          encode_strconsole(nameuser),
                          "/t"], stderr=STDOUT)

        except Exception as e:
            logger.error("\n%s"%(traceback.format_exc()))

def cleandescriptor(datasend):

    if sys.platform.startswith('linux'):
        try:
            del datasend['descriptor']['win']
        except KeyError:
            pass
        try:
            del datasend['descriptor']['mac']
        except KeyError:
            pass
        try:
            datasend['descriptor']['sequence'] = datasend['descriptor']['linux']['sequence']
            del datasend['descriptor']['linux']
        except:
            return False

    elif sys.platform.startswith('win'):
        try:
            del datasend['descriptor']['linux']
        except KeyError:
            pass
        try:
            del datasend['descriptor']['mac']
        except KeyError:
            pass
        try:
            datasend['descriptor']['sequence'] = datasend['descriptor']['win']['sequence']
            #del datasend['descriptor']['win']['sequence']
            del datasend['descriptor']['win']
        except:
            return False
    elif sys.platform.startswith('darwin'):
        try:
            del datasend['descriptor']['linux']
        except KeyError:
            pass
        try:
            del datasend['descriptor']['win']
        except KeyError:
            pass
        try:
            datasend['descriptor']['sequence'] = datasend['descriptor']['mac']['sequence']
            #del datasend['descriptor']['Macos']['sequence']
            del datasend['descriptor']['mac']
        except:
            return False
    datasend['typeos'] = sys.platform
    return True

def create_message_self_for_transfertfile(sessionid):
    return  {
        'action': plugin['NAME'],
        'sessionid': sessionid,
        'data' :{'step' : "transferfiles"},
        'ret' : 0,
        'base64' : False}

def askinfo(to, sessionid, objectxmpp, informationasking=[], replyaction=None,
            list_to_sender=[], step=None):
    ask = {
        'action': "requestinfo",
        'sessionid': sessionid,
        'data' : {'actiontype' : 'requestinfo'},
        'ret' : 0,
        'base64' : False}

    if replyaction is not None:
        ask['data']['actionasker'] = replyaction
    if len(list_to_sender) != 0:
        ask['data']['sender'] = list_to_sender
    if step is not None:
        ask['data']['step'] = step
    if len(informationasking) != 0:
        ask['data']['dataask'] = informationasking

    objectxmpp.send_message(mto = to,
                            mbody = json.dumps(ask),
                            mtype = 'chat')

def takeresource(datasend, objectxmpp, sessionid):
    datasendl = {}
    if not 'data' in datasend:
        datasendl['data'] = datasend
    else:
        datasendl = datasend

    logger.debug('take ressourse : %s'%datasendl['data']['jidrelay'])
    msgresource = {'action': "cluster",
                    'sessionid': sessionid,
                    'data' :  {"subaction" : "takeresource",
                                "data" : {'user' : datasendl['data']['advanced']['login'],
                                        'machinejid' : datasendl['data']['jidmachine']
                                }
                    },
                    'ret' : 0,
                    'base64' : False}
    objectxmpp.send_message(mto = datasendl['data']['jidrelay'],
                            mbody = json.dumps(msgresource),
                            mtype = 'chat')
    objectxmpp.xmpplog('take resource : %s'%datasendl['data']['jidrelay'],
                       type = 'deploy',
                       sessionname = sessionid,
                       priority = -1,
                       action = "",
                       who = objectxmpp.boundjid.bare,
                       how = "",
                       why = "",
                       module = "Deployment| Notify | Cluster",
                       date = None ,
                       fromuser = datasendl['data']['advanced']['login'],
                       touser = "")
    return datasend

def removeresource(datasend, objectxmpp, sessionid):
    datasendl = {}
    if not 'data' in datasend:
        datasendl['data'] = datasend
    else:
        datasendl = datasend
    logger.debug('restores ressource : %s'%datasendl['data']['jidrelay'])
    msgresource = {'action': "cluster",
                    'sessionid': sessionid,
                    'data' :  { "subaction" : "removeresource",
                                "data" : {'user' : datasendl['data']['advanced']['login'],
                                            'machinejid' : datasendl['data']['jidmachine']
                                }
                    },
                    'ret' : 0,
                    'base64' : False}
    objectxmpp.send_message(mto = datasendl['data']['jidrelay'],
                            mbody = json.dumps(msgresource),
                            mtype = 'chat')
    objectxmpp.xmpplog('restores ressource : %s'%datasendl['data']['jidrelay'],
                       type = 'deploy',
                       sessionname = sessionid,
                       priority = -1,
                       action = "",
                       who = objectxmpp.boundjid.bare,
                       how = "",
                       why = "",
                       module = "Deployment| Notify | Cluster",
                       date = None ,
                       fromuser = datasendl['data']['advanced']['login'],
                       touser = "")
    return datasend

def initialisesequence(datasend, objectxmpp, sessionid ):
    strjidagent = str(objectxmpp.boundjid.bare)
    datasend['data']['stepcurrent'] = 0 #step initial
    if not objectxmpp.session.isexist(sessionid):
        logger.debug("creation session %s"%sessionid)
        objectxmpp.session.createsessiondatainfo(sessionid,  datasession = datasend['data'], timevalid = 180)
        logger.debug("update object backtodeploy")

    logger.debug("start call gracet (initiation)")
    objectxmpp.xmpplog('START DEPLOY AFTER TRANSFERT FILES : %s'%datasend['data']['name'],
                        type = 'deploy',
                        sessionname = sessionid,
                        priority = -1,
                        action = "",
                        who = strjidagent,
                        how = "",
                        why = "",
                        module = "Deployment| Notify | Execution | Scheduled",
                        date = None ,
                        fromuser = datasend['data']['advanced']['login'],
                        touser = "")
    logger.debug("start call gracet (initiation)")
    if 'data' in datasend and \
                'descriptor' in datasend['data'] and \
                'path' in datasend['data'] and \
                "info" in datasend['data']['descriptor'] and \
                "launcher" in  datasend['data']['descriptor']['info']:
        try:
            id_package = os.path.basename(datasend['data']['path'])
            if id_package != "":
                name = datasend['data']['name']
                commandlauncher = base64.b64decode(datasend['data']['descriptor']['info']['launcher'])
                objectxmpp.infolauncherkiook.set_cmd_launch(id_package, commandlauncher)
                #addition correspondance name et idpackage.
                if name != "":
                    objectxmpp.infolauncherkiook.set_ref_package_for_name(name, id_package)
                    objectxmpp.xmpplog("launcher command for kiosk [%s] - [%s] -> [%s]"%(commandlauncher, name, id_package),
                                type = 'deploy',
                                sessionname = datasend['sessionid'],
                                priority = -1,
                                action = "",
                                who = strjidagent,
                                how = "",
                                why = "",
                                module = "Deployment | Kiosk",
                                date = None ,
                                fromuser = str(datasend['data']['advanced']['login']),
                                touser = "")
                else:
                    logger.warning("nanme missing for info launcher command of kiosk")
            else:
                logger.warning("id package missing for info launcher command of kiosk")
        except:
            logger.error("launcher command of kiosk")
            traceback.print_exc(file=sys.stdout)
    else:
        logger.warning("launcher command missing for kiosk")
    grafcet(objectxmpp, datasend)
    logger.debug("outing graphcet end initiation")

def curlgetdownloadfile( destfile, urlfile, insecure = True, limit_rate_ko= None):
    # As long as the file is opened in binary mode, both Python 2 and Python 3
    # can write response body to it without decoding.
    with open(destfile, 'wb') as f:
        c = pycurl.Curl()
        urlfile=urlfile.replace(" ", "%20")
        c.setopt(c.URL, urlfile)
        c.setopt(c.WRITEDATA, f)
        if limit_rate_ko is not None and limit_rate_ko != '' and int(limit_rate_ko) > 0:
            # limit_rate_ko en octed in curl
            c.setopt(c.MAX_RECV_SPEED_LARGE, int(limit_rate_ko)*1024)
        if insecure :
            # option equivalent a friser de --insecure
            c.setopt(pycurl.SSL_VERIFYPEER, 0)
            c.setopt(pycurl.SSL_VERIFYHOST, 0)
        c.perform()
        c.close()

def pull_package_transfert_rsync(datasend, objectxmpp, ippackage, sessionid, cmdmode="rsync"):
    #print json.dumps( datasend, indent = 4)
    logger.info("###################################################")
    logger.info("pull_package_transfert_rsync : " + cmdmode)
    logger.info("###################################################")
    takeresource(datasend, objectxmpp, sessionid)
    strjidagent = str(objectxmpp.boundjid.bare)
    try:
        #packagename = datasend['data']['descriptor']['info']['packageUuid']
        packagename = os.path.basename(datasend['data']['pathpackageonmachine'])
        userpackage = "userpackage"
        remotesrc = """%s@%s:'%s' """%(userpackage , ippackage, packagename)
        execrsync = "rsync"
        execscp   = "scp"
        error=False
        if sys.platform.startswith('linux'):
            path_key_priv =  os.path.join("/", "var", "lib", "pulse2", ".ssh", "id_rsa")
            #path_key_priv =  os.path.join("/", "root", ".ssh", "id_rsa")
            localdest = " '%s/%s'"%(managepackage.packagedir(), packagename)
        elif sys.platform.startswith('win'):
            path_key_priv =  os.path.join("c:\Users\pulseuser", ".ssh", "id_rsa")
            localdest = " '%s/%s'"%(managepackage.packagedir(), packagename)
            if platform.machine().endswith('64'):
                execrsync = "C:\\\\Windows\\\\SysWOW64\\\\rsync.exe"
            else:
                execrsync = "C:\\\\Windows\\\\System32\\\\rsync.exe"
            execscp   = os.path.join(os.environ["ProgramFiles"], "OpenSSH", "scp.exe")
        elif sys.platform.startswith('darwin'):
            path_key_priv =  os.path.join("/", "var", "root", ".ssh", "id_rsa")
            localdest = " '%s/%s'"%(managepackage.packagedir(), packagename)
        else :
            return False
        cmdtransfert = "%s -C -r "%execscp
        if cmdmode == "rsync":
            cmdtransfert =  " %s -z --rsync-path=rsync "%execrsync
        cmd = """%s -e "ssh -o IdentityFile=%s -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o Batchmode=yes -o PasswordAuthentication=no -o ServerAliveInterval=10 -o CheckHostIP=no -o LogLevel=ERROR -o ConnectTimeout=10" -av --chmod=777 """%(cmdtransfert, path_key_priv)
        cmdexec =  cmd + remotesrc + localdest
        objectxmpp.xmpplog("cmd transfert is : \n %s"%cmdexec,
                    type = 'deploy',
                    sessionname = datasend['sessionid'],
                    priority = -1,
                    action = "",
                    who = strjidagent,
                    how = "",
                    why = "",
                    module = "Deployment | Download | Transfert",
                    date = None ,
                    fromuser = datasend['data']['advanced']['login'],
                    touser = "")
        obj = simplecommand(cmdexec)
        if obj['code'] != 0:
            objectxmpp.xmpplog("cmd result : \n %s"%obj['result'],
                                type = 'deploy',
                                sessionname = datasend['sessionid'],
                                priority = -1,
                                action = "",
                                who = strjidagent,
                                how = "",
                                why = "",
                                module = "Deployment | Download | Transfert",
                                date = None ,
                                fromuser = datasend['data']['advanced']['login'],
                                touser = "")
            cmdexec = cmdexec.replace("pulseuser","pulse")
            objectxmpp.xmpplog("test cmd transfert is : \n %s"%cmdexec,
                                type = 'deploy',
                                sessionname = datasend['sessionid'],
                                priority = -1,
                                action = "",
                                who = strjidagent,
                                how = "",
                                why = "",
                                module = "Deployment | Download | Transfert",
                                date = None ,
                                fromuser = datasend['data']['advanced']['login'],
                                touser = "")
            obj = simplecommandstr(cmdexec)
            if obj['code'] != 0:
                objectxmpp.xmpplog("cmd result : \n %s"%obj['result'],
                                type = 'deploy',
                                sessionname = datasend['sessionid'],
                                priority = -1,
                                action = "",
                                who = strjidagent,
                                how = "",
                                why = "",
                                module = "Deployment | Download | Transfert",
                                date = None ,
                                fromuser = datasend['data']['advanced']['login'],
                                touser = "")
                error=True
                return False
        error=False
        return True
    except Exception:
        logger.error("\n%s"%(traceback.format_exc()))
        error=True
        return False
    finally:
        removeresource(datasend, objectxmpp, sessionid)
        signalendsessionforARS(datasend , objectxmpp, sessionid, error = error)

def recuperefile(datasend, objectxmpp, ippackage, portpackage, sessionid):
    strjidagent = str(objectxmpp.boundjid.bare)
    if not os.path.isdir(datasend['data']['pathpackageonmachine']):
        os.makedirs(datasend['data']['pathpackageonmachine'], mode=0777)
    uuidpackage = datasend['data']['path'].split('/')[-1]
    curlurlbase = "https://%s:%s/mirror1_files/%s/"%(ippackage, portpackage, uuidpackage )
    takeresource(datasend, objectxmpp, sessionid)
    objectxmpp.xmpplog("package server is %s"%curlurlbase,
                       type = 'deploy',
                       sessionname = datasend['sessionid'],
                       priority = -1,
                       action = "",
                       who = strjidagent,
                       how = "",
                       why = "",
                       module = "Deployment | Download | Transfert",
                       date = None ,
                       fromuser = datasend['data']['advanced']['login'],
                       touser = "")

    for filepackage in datasend['data']['packagefile']:
        if datasend['data']['methodetransfert'] == "pullcurl":
            dest = os.path.join(datasend['data']['pathpackageonmachine'], filepackage)
            urlfile = curlurlbase + filepackage

            logger.info("###################################################")
            logger.info("adress telechargement package par le client en curl : " + urlfile)
            logger.info("###################################################")
            try:
                if 'limit_rate_ko' in datasend['data']['descriptor']['info'] and \
                                datasend['data']['descriptor']['info']['limit_rate_ko'] != "" and\
                                    int(datasend['data']['descriptor']['info']['limit_rate_ko'])> 0:
                    limit_rate_ko = datasend['data']['descriptor']['info']['limit_rate_ko']
                    msg = 'download  file : %s Package : %s <span style="font-weight: bold;color : orange;">[transfert rate %s ko]</span>'%( filepackage, datasend['data']['name'],limit_rate_ko)
                else:
                    limit_rate_ko = ""
                    msg = 'download  file : %s Package : %s'%( filepackage, datasend['data']['name'])
                objectxmpp.xmpplog( msg,
                                    type = 'deploy',
                                    sessionname = datasend['sessionid'],
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Download | Transfert",
                                    date = None ,
                                    fromuser = datasend['data']['advanced']['login'],
                                    touser = "")
                curlgetdownloadfile( dest, urlfile, insecure = True, limit_rate_ko = limit_rate_ko)
                changown_dir_of_file(dest)# owner pulse or pulseuser.
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                logger.debug(str(e))
                objectxmpp.xmpplog('<span style="font-weight: bold;color : red;">STOP DEPLOY ON ERROR : download curl [%s] file package : %s</span>'%(curlurlbase, filepackage),
                                    type = 'deploy',
                                    sessionname = datasend['sessionid'],
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Download | Transfert | Notify | Error",
                                    date = None ,
                                    fromuser = datasend['data']['name'],
                                    touser = "")
                objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = datasend['sessionid'],
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Error | Terminate | Notify",
                                    date = None ,
                                    fromuser = datasend['data']['name'],
                                    touser = "")
                removeresource(datasend, objectxmpp, sessionid)
                signalendsessionforARS(datasend , objectxmpp, sessionid, error = True)
                return False
    removeresource(datasend, objectxmpp, sessionid)
    signalendsessionforARS(datasend , objectxmpp, sessionid, error = False)
    return True

def signalendsessionforARS(datasend , objectxmpp, sessionid, error = False):
    #termine sessionid sur ARS pour permettre autre deploiement
    try :
        msgsessionend = { 'action': "resultapplicationdeploymentjson",
                        'sessionid': sessionid,
                        'data' :  datasend,
                        'ret' : 255,
                        'base64' : False
                        }
        if error == False:
            msgsessionend['ret'] = 0
        datasend['endsession'] = True
        objectxmpp.send_message(mto=datasend['data']['jidrelay'],
                                mbody=json.dumps(msgsessionend),
                                mtype='chat')
    except Exception as e:
        logger.debug(str(e))
        traceback.print_exc(file=sys.stdout)


def action( objectxmpp, action, sessionid, data, message, dataerreur):
    strjidagent = str(objectxmpp.boundjid.bare)
    if hasattr(objectxmpp.config, 'clients_ssh_port'):
        Globaldata['port_local'] = int(objectxmpp.config.clients_ssh_port)
        logger.debug("Clients SSH port %s"%Globaldata['port_local'])
    if objectxmpp.config.agenttype in ['machine']:
        logger.debug("###################################################")
        logger.debug("call %s from %s"%(plugin,message['from']))
        logger.debug("###################################################")
        logger.debug("#################AGENT MACHINE#####################")
        logger.debug("###################################################")

        # If actionscheduler is set, the message comes from master to specify what to do
        # between: run, abandonmentdeploy and pause
        if 'actionscheduler' in data:
            if data['actionscheduler'] == "run":
                logger.debug("RUN DEPLOY")
                sessioninfo  = objectxmpp.Deploybasesched.get_sesionscheduler(sessionid)
                if sessioninfo == "":
                    objectxmpp.xmpplog('<span style="font-weight: bold;color : red;">Erreur execution package after tranfert files Scheduling erreur session missing</span>',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Error  | Notify | Execution",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                    objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate |Notify",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                    signalendsessionforARS(data , objectxmpp, sessionid, error = True)
                    return
                else:
                    datajson =  json.loads(sessioninfo)
                    datasend = datajson
                    #"Supprime dans base"
                    objectxmpp.Deploybasesched.del_sesionscheduler(sessionid)
                    initialisesequence(datasend, objectxmpp, sessionid)
                    return
            elif data['actionscheduler'] == "pause":

                return
            elif data['actionscheduler'] == "abandonmentdeploy":
                objectxmpp.xmpplog('<span style="font-weight: bold;color : red;">DEPLOY SCHEDULED : ABANDONNED</span>',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Error | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                #clear sessionscheduler
                objectxmpp.Deploybasesched.del_sesionscheduler(sessionid)
                signalendsessionforARS(data , objectxmpp, sessionid, error = True)
            else:
                #supprime cet input
                objectxmpp.xmpplog('<span style="font-weight: bold;color : red;">DEPLOY SCHEDULED : ERROR</span>',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Error | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                objectxmpp.Deploybasesched.del_sesionscheduler(sessionid)
                signalendsessionforARS(data , objectxmpp, sessionid, error = True)
            return


        #when dependence require, AM asks ARS for this dependency
        #If a dependency does not exist, relay server reports it by sending "error package missing"
        if 'descriptor' in data and data['descriptor'] == "error package missing":
            #package data['deploy'] is missing
            #termined le deploy
            objectxmpp.xmpplog('<span style="font-weight: bold;color : red;">STOP DEPLOY ON ERROR : DEPENDENCY MISSING [%s]</span>'%data['deploy'],
                                type = 'deploy',
                                sessionname = sessionid,
                                priority = -1,
                                action = "",
                                who = strjidagent,
                                how = "",
                                why = "",
                                module = "Deployment | Error | Dependencies | Transfert| Notify",
                                date = None ,
                                fromuser = data['name'],
                                touser = "")
            if sessionid in objectxmpp.back_to_deploy:
                objectxmpp.xmpplog('<span style="font-weight: bold;color : red;">List of abandoned dependencies %s</span>'%objectxmpp.back_to_deploy[sessionid]['Dependency'],
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Dependencies | Transfert | Notify",
                                    date = None ,
                                    fromuser = data['name'],
                                    touser = "")
            objectxmpp.xmpplog( 'DEPLOYMENT TERMINATE',
                                type = 'deploy',
                                sessionname = sessionid,
                                priority = -1,
                                action = "",
                                who = strjidagent,
                                how = "",
                                why = "",
                                module = "Deployment | Terminate | Notify",
                                date = None ,
                                fromuser =data['name'],
                                touser = "")
            signalendsessionforARS(data , objectxmpp, sessionid, error = True)

            #clean session
            objectxmpp.session.clearnoevent(sessionid)
            #clean if not session
            cleanbacktodeploy(objectxmpp)
            return

        # condition for quit deploy reinjection de message avec condition error
        # data is empty message for gestion des dependency
        if len(data) == 0:
            if 'msgstate' in message['body'] and 'msg' in message['body']['msgstate']  and message['body']['msgstate']['msg'].startswith("end error"):
                if message['body']['msgstate']['quitonerror']:
                    logger.debug("Quit session %s on error "%sessionid)
                    objectxmpp.xmpplog('<span style="font-weight: bold;color : red;">STOP DEPLOY ON ERROR</span>',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Error",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                    if sessionid in objectxmpp.back_to_deploy:
                        objectxmpp.xmpplog('<span style="font-weight: bold;color : red;">List of abandoned dependencies %s</span>'%objectxmpp.back_to_deploy[sessionid]['Dependency'],
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Dependencies | Transfert | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                    objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                    objectxmpp.session.clearnoevent(sessionid)
                    cleanbacktodeploy(objectxmpp)
                    return

            #signal deploy terminate si session n'ai pas dans back_to_deploy
            if sessionid not in objectxmpp.back_to_deploy:
                # Deployment to finish here.
                logger.debug("termine la session %s"%sessionid)
                objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                objectxmpp.session.clearnoevent(sessionid)
                cleanbacktodeploy(objectxmpp)
                return

            if sessionid in objectxmpp.back_to_deploy and 'Dependency' in objectxmpp.back_to_deploy[sessionid]:
                if len(objectxmpp.back_to_deploy[sessionid]['Dependency']) > 0:
                    loaddependency = objectxmpp.back_to_deploy[sessionid]['Dependency'].pop()
                    data = copy.deepcopy(objectxmpp.back_to_deploy[sessionid]['packagelist'][loaddependency])
                    objectxmpp.xmpplog( '! : dependency [%s] '%(data['name']),
                                        type = 'deploy',
                                        sessionname = sessionid,
                                        priority = -1,
                                        action = "",
                                        who = strjidagent,
                                        how = "",
                                        why = "",
                                        module = "Deployment | Dependency",
                                        date = None ,
                                        fromuser = "AM %s"% strjidagent,
                                        touser = "")
                    try:
                        objectxmpp.back_to_deploy[sessionid]['Dependency'].remove(loaddependency)
                    except Exception:
                        pass
                    del(objectxmpp.back_to_deploy[sessionid]['packagelist'][loaddependency])
                    if len(objectxmpp.back_to_deploy[sessionid]['Dependency']) == 0:
                        del(objectxmpp.back_to_deploy[sessionid])
                    save_back_to_deploy(objectxmpp.back_to_deploy)
                    objectxmpp.session.sessionsetdata(sessionid, data)
                    #objectxmpp.session.clearnoevent(sessionid)


        #il y a des dependences dans package
        if 'Dependency' in data['descriptor']['info'] and  len (data['descriptor']['info'] ['Dependency']) != 0:
            # Not immediately deployed
            # The deployment is prepared for the next
            try:
                if not sessionid in objectxmpp.back_to_deploy:
                    objectxmpp.back_to_deploy[sessionid] = {}
                    objectxmpp.back_to_deploy[sessionid]['Dependency'] = []
                    objectxmpp.back_to_deploy[sessionid]['packagelist'] = {}

                data['deploy'] = data['path'].split("/")[-1]
                data['descriptor']['info']['Dependency'].reverse()
                data['descriptor']['info']['Dependency'].insert(0,data['deploy'] )
                objectxmpp.back_to_deploy[sessionid]['Dependency'] = objectxmpp.back_to_deploy[sessionid]['Dependency'] + data['descriptor']['info']['Dependency']
                del data['descriptor']['info']['Dependency']
                logger.debug("Dependency deployement %s"%(objectxmpp.back_to_deploy[sessionid]['Dependency']))
                #global information to keep for this session


                if not 'ipmachine' in objectxmpp.back_to_deploy[sessionid]:
                    #on les sauves
                    #toutes les dependences du packet deploye hérite des priorites de ce packet.
                    objectxmpp.back_to_deploy[sessionid]['ipmachine'] = data['ipmachine']
                    objectxmpp.back_to_deploy[sessionid]['ipmaster'] = data['ipmaster']
                    objectxmpp.back_to_deploy[sessionid]['iprelay'] = data['iprelay']
                    objectxmpp.back_to_deploy[sessionid]['jidmachine'] = data['jidmachine']
                    objectxmpp.back_to_deploy[sessionid]['jidmaster'] = data['jidmaster']
                    objectxmpp.back_to_deploy[sessionid]['jidrelay'] = data['jidrelay']
                    objectxmpp.back_to_deploy[sessionid]['login'] = data['login']
                    objectxmpp.back_to_deploy[sessionid]['methodetransfert'] = data['methodetransfert']
                    objectxmpp.back_to_deploy[sessionid]['transfert'] = data['transfert']
                    objectxmpp.back_to_deploy[sessionid]['uuid'] = data['uuid']
                    objectxmpp.back_to_deploy[sessionid]['ippackageserver'] = data['ippackageserver']
                    objectxmpp.back_to_deploy[sessionid]['portpackageserver'] = data['portpackageserver']
                    if 'advanced' in data:
                        objectxmpp.back_to_deploy[sessionid]['advanced'] = data['advanced']
            except Exception as e:
                logger.error(str(e))

        if sessionid in objectxmpp.back_to_deploy and not 'start' in objectxmpp.back_to_deploy[sessionid]:
            #create list package deploy
            try:
                # Necessary datas are added.
                # If we do not have these data global has all the dislocation we add them.
                # Son applique a la dependence les proprietes du packages
                if not 'ipmachine' in data:
                    logger.debug("addition global informations for deploy mode push dependency")
                    data['ipmachine'] = objectxmpp.back_to_deploy[sessionid]['ipmachine']
                    data['ipmaster'] = objectxmpp.back_to_deploy[sessionid]['ipmaster']
                    data['iprelay'] = objectxmpp.back_to_deploy[sessionid]['iprelay']
                    data['jidmachine'] = objectxmpp.back_to_deploy[sessionid]['jidmachine']
                    data['jidmaster'] = objectxmpp.back_to_deploy[sessionid]['jidmaster']
                    data['login'] = objectxmpp.back_to_deploy[sessionid]['login']
                    data['methodetransfert'] = objectxmpp.back_to_deploy[sessionid]['methodetransfert']
                    data['transfert'] = objectxmpp.back_to_deploy[sessionid]['transfert']
                    data['uuid'] = objectxmpp.back_to_deploy[sessionid]['uuid']
                    data['jidrelay'] = objectxmpp.back_to_deploy[sessionid]['jidrelay']
                    data['ippackageserver'] = objectxmpp.back_to_deploy[sessionid]['ippackageserver']
                    data['portpackageserver'] = objectxmpp.back_to_deploy[sessionid]['portpackageserver']
                    if 'advanced' in objectxmpp.back_to_deploy[sessionid]:
                        data['advanced'] =  objectxmpp.back_to_deploy[sessionid]['advanced']

                # Verify that for each Dependency one has its descriptor
                # Store the dependency descriptor in back_to_deploy object for the session
                data['deploy'] = data['path'].split("/")[-1]
                if not data['deploy'] in objectxmpp.back_to_deploy[sessionid]:
                    objectxmpp.back_to_deploy[sessionid]['packagelist'][data['deploy']] = data
                if not 'count' in objectxmpp.back_to_deploy[sessionid]:
                    #We use a counter to take a case where the dependencies loop.
                    objectxmpp.back_to_deploy[sessionid]['count'] = 0
                # Then we look in the list of descriptors if these data of each dependence are present
                for dependency in objectxmpp.back_to_deploy[sessionid]['Dependency']:
                    if dependency == "": continue

                    if not dependency in objectxmpp.back_to_deploy[sessionid]['packagelist']:
                        #on demande a (rs pakage server) de nous envoyé le descripteurs de ce package
                        datasend = {
                            'action': "rsapplicationdeploymentjson",
                            'sessionid': sessionid,
                            'data' : { 'deploy' : dependency},
                            'ret' : 0,
                            'base64' : False
                        }
                        objectxmpp.back_to_deploy[sessionid]['count']+= 1
                        if objectxmpp.back_to_deploy[sessionid]['count'] > 30:
                            objectxmpp.xmpplog( 'Warning [%s] verify cyclic dependencies'%(dependency),
                                        type = 'deploy',
                                        sessionname = sessionid,
                                        priority = -1,
                                        action = "",
                                        who = strjidagent,
                                        how = "",
                                        why = "",
                                        module = "Deployment | Dependency",
                                        date = None ,
                                        fromuser = "AM %s"% strjidagent,
                                        touser = "")
                            return
                        # If it lacks a dependency descriptor it is requested to relay server
                        objectxmpp.send_message(   mto = data['jidrelay'],
                                                    mbody = json.dumps(datasend),
                                                    mtype = 'chat')
                        if sessionid in objectxmpp.back_to_deploy:
                            save_back_to_deploy(objectxmpp.back_to_deploy)
                        return
                else:
                    # All dependencies are taken into account.
                    # You must deploy the descriptors of the dependency list starting with the end (pop)
                    #objectxmpp.back_to_deploy[sessionid]['Dependency']
                    #logger.debug("Start Multi-dependency deployment.")
                    strdeploypack = []
                    packlistdescribemapdeploy = []
                    for k in objectxmpp.back_to_deploy[sessionid]['Dependency']:
                        if not k in packlistdescribemapdeploy:
                            packlistdescribemapdeploy.append(str(k))
                            strdeploypack.append(objectxmpp.back_to_deploy[sessionid]['packagelist'][k]['descriptor']['info']['software'])
                    objectxmpp.back_to_deploy[sessionid]['Dependency'] = packlistdescribemapdeploy
                    strdeploypack.reverse()
                    objectxmpp.xmpplog('(Prepare the Deployment Plan for %s : [%s])'%( strdeploypack[-1], ", ".join(strdeploypack)),
                                        type = 'deploy',
                                        sessionname = sessionid,
                                        priority = -1,
                                        action = "",
                                        who = strjidagent,
                                        how = "",
                                        why = "",
                                        module = "Deployment",
                                        date = None ,
                                        fromuser = data['name'],
                                        touser = "")

                    logger.debug("Dependencies list %s"%(objectxmpp.back_to_deploy[sessionid]['Dependency']))
                    firstinstall = objectxmpp.back_to_deploy[sessionid]['Dependency'].pop()

                    objectxmpp.back_to_deploy[sessionid]['start'] = True

                    data = copy.deepcopy(objectxmpp.back_to_deploy[sessionid]['packagelist'][firstinstall])
                    #objectxmpp.xmpplog('! : first dependency [%s] '%(data['name']),
                                        #type = 'deploy',
                                        #sessionname = sessionid,
                                        #priority = -1,
                                        #action = "",
                                        #who = strjidagent,
                                        #how = "",
                                        #why = "",
                                        #module = "Deployment",
                                        #date = None ,
                                        #fromuser = data['name'],
                                        #touser = "")
                    try:
                        # Removes all the occurrences of this package if it exists because it is installing
                        objectxmpp.back_to_deploy[sessionid]['Dependency'].remove(firstinstall)
                    except Exception:
                        pass
                    del(objectxmpp.back_to_deploy[sessionid]['packagelist'][firstinstall])
                    save_back_to_deploy(objectxmpp.back_to_deploy)
            #########################################################
            except Exception as e:
                logger.error(str(e))

        if sessionid in objectxmpp.back_to_deploy:
            # Necessary datas are added.
            # If one has not in data this information is added.
            if not 'ipmachine' in data:
                logger.debug("addition global informations for deploy")
                data['ipmachine'] = objectxmpp.back_to_deploy[sessionid]['ipmachine']
                data['ipmaster'] = objectxmpp.back_to_deploy[sessionid]['ipmaster']
                data['iprelay'] = objectxmpp.back_to_deploy[sessionid]['iprelay']
                data['jidmachine'] = objectxmpp.back_to_deploy[sessionid]['jidmachine']
                data['jidmaster'] = objectxmpp.back_to_deploy[sessionid]['jidmaster']
                data['login'] = objectxmpp.back_to_deploy[sessionid]['login']
                data['methodetransfert'] = objectxmpp.back_to_deploy[sessionid]['methodetransfert']
                data['transfert'] = objectxmpp.back_to_deploy[sessionid]['transfert']
                data['uuid'] = objectxmpp.back_to_deploy[sessionid]['uuid']
                data['jidrelay'] = objectxmpp.back_to_deploy[sessionid]['jidrelay']
                data['ippackageserver'] = objectxmpp.back_to_deploy[sessionid]['ippackageserver']
                data['portpackageserver'] = objectxmpp.back_to_deploy[sessionid]['portpackageserver']
                if 'advanced' in objectxmpp.back_to_deploy[sessionid]:
                    data['advanced'] =  objectxmpp.back_to_deploy[sessionid]['advanced']
            objectxmpp.session.sessionsetdata(sessionid, data)

        datasend = {
                        'action': action,
                        'sessionid': sessionid,
                        'data' : data,
                        'ret' : 0,
                        'base64' : False
                    }


        if not 'stepcurrent' in datasend['data']:
            if not cleandescriptor(data):
                objectxmpp.xmpplog('<span style="color: red;";>[xxx]: Terminate deploy ERROR descriptor OS %s missing</span>'%sys.platform,
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = 0,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment",
                                    date = None ,
                                    fromuser = datasend['data']['name'],
                                    touser = "")
                datasend = {
                                'action':  "result" + action,
                                'sessionid': sessionid,
                                'data' : data,
                                'ret' : -1,
                                'base64' : False
                }
                datasend['data']['descriptor']['sequence']=[{"action" : "ERROR",
                                                            "description" : "DESCRIPTOR MISSING FOR Paltform %s os[%s]"%(sys.platform,platform.platform()),
                                                            "step" : -1,
                                                            "completed" : 1}]

                objectxmpp.send_message(   mto='log@pulse',
                                                mbody = json.dumps(datasend),
                                                mtype = 'chat')
                objectxmpp.send_message(   mto=data['jidmaster'],
                                                mbody = json.dumps(datasend),
                                                mtype = 'chat')

                objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                signalendsessionforARS(data , objectxmpp, sessionid, error = True)
                return
            else:
                datasend = {
                                'action': action,
                                'sessionid': sessionid,
                                'data' : data,
                                'ret' : 0,
                                'base64' : False
                }
            datasend['data']['pathpackageonmachine'] = os.path.join( managepackage.packagedir(),data['path'].split('/')[-1])

            ### data['methodetransfert'] =  'pullrsync'
            if data['transfert'] and data['methodetransfert'] in ["pullcurl"]:
                #pull method download file
                recupfile = recuperefile(datasend,
                                         objectxmpp,
                                         data['ippackageserver'],
                                         data['portpackageserver'],
                                         sessionid)
                #removeresource(datasend, objectxmpp, sessionid)
                if not recupfile:
                    logger.debug("Error Pull method transfert file")
                    datasend = {
                                'action':  "result" + action,
                                'sessionid': sessionid,
                                'data' : data,
                                'ret' : -1,
                                'base64' : False
                    }
                    objectxmpp.send_message(   mto='log@pulse',
                                                    mbody = json.dumps(datasend),
                                                    mtype = 'chat')
                    objectxmpp.send_message(   mto=data['jidmaster'],
                                                    mbody = json.dumps(datasend),
                                                    mtype = 'chat')
                    objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% strjidagent,
                                    touser = "")
                    #signalendsessionforARS(data , objectxmpp, sessionid, error = True)

                    # termine sesion on error
                    # clean session
                    objectxmpp.session.clearnoevent(sessionid)
                    # clean if not session
                    cleanbacktodeploy(objectxmpp)
                    return
                else:
                    # Pull transfer complete
                    # send message to master for updatenbdeploy
                    datasend1 = {'action':  "updatenbdeploy",
                                 'sessionid' : sessionid,
                                 'data' : data['advanced'],
                                 'ret' : 1,
                                 'base64' : False}
                    # send sessionid message to master with cmdid files installed
                    # update base has_login_command count_deploy_progress
                    objectxmpp.send_message(mto=data['jidmaster'],
                                            mbody = json.dumps(datasend1),
                                            mtype = 'chat')

            if not 'advanced' in datasend['data']:
                datasend['data']['advanced'] = {}
                datasend['data']['advanced']['exec'] = True

            if datasend['data']['advanced']['exec'] == True or not 'advanced' in datasend['data']:
                # deploy directly
                datasend['data']['advanced']['scheduling'] = False
                initialisesequence(datasend, objectxmpp, sessionid)
            else:
                # schedule deployment
                objectxmpp.xmpplog('DEPLOY PACKAGE IN PAUSE : %s'%data['name'],
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Notify",
                                    date = None ,
                                    fromuser = data['advanced']['login'],
                                    touser = "")
                datasend['data']['advanced']['scheduling'] = True
                objectxmpp.Deploybasesched.set_sesionscheduler(sessionid,json.dumps(datasend))
        else:
            objectxmpp.session.sessionsetdata(sessionid, datasend) #save data in session
            grafcet(objectxmpp, datasend) #grafcet will use the session
            logger.debug("outing graphcet phase1")
    else:
        logger.debug("###################################################")
        logger.debug("##############AGENT RELAY SERVER###################")
        logger.debug("###################################################")
        # nota doc
        # a la réception d'un descripteur de deploiement, si plusieurs ARS sont dans le cluster,
        # on détermine quel ARS doit faire le deploiement. le descripteur est alors redirigé vers ARS qui doit deployé.
        # le descripteur transmit a alors une clef cluster avec comme valeur le (jid de ARS) qui soustraite le déploiement.
        # ARS qui recois ce descripteur assure le déploiement.



        # qui deploy dans le cluster.
        # Pour déterminer ARS qui deploye dans le cluster, on choisie ARS avec le plus petit coefficient de charge.
        # le coefficient de charge de deploiement de chaque ARS est connu par tout les ARS du cluster.
        # a la prise en compte d'un deploiement, ce coefficient  de charge est modifier,
        # alors tous les autre ARS du cluster recoive une notification permettant de tenir à jour ce coefficient.

        # Ce qui definie la charge d'un aRs, c'est le nombre de deploiement en cours( transfert de fichier non fait ou non terminer.)
        # si le transfert de fichiers est fait et terminé , alors ce deploiement n'est plus totalisé comme une charge pour ARS.
        # donc le coefficient de charge est diminué une fois un transfert de fichier terminé.
        # alors tous les autre ARS du cluster recoive une notification permettant de tenir à jour ce coefficient.

        # consernant les deploiement avec dépendances, tous les deployement des packages sont effectué par un meme ARS.


        # autre prise ne compte de charge d'un cluster.
        # on peut avoir une demande tres importantes de deploiements demandé a sur un ARS, meme au sein d'un cluster.
        # On a donc besoin d'un systeme de lissage de la charge ponctuel, pour que celle-ci soit dilué dans le temps.
        # pour cela, on définie un nombre maximun de deploiement simultané.
        # les deploiement sont empilés dans une pile LILO, puis dépilé est deployé pour avoir toujour une charge inférieur au nombre de deploiement simultanée demandé.
        # on utilisera une base non sql pour conservé les descripteurs en attente de deploiement.
        # ainsi on assurera une persistance en cas d'arrêt de ARS. les deploiements encore dans la base seront
        # effectués a la remise en fonction de ARS.
        #initialise charge_apparente_cluster si non initialiser
        if not "login" in data:
            data['login']= ""
        add_chargeapparente(objectxmpp, strjidagent)
        clear_chargeapparente(objectxmpp)

        #si parameter avanced spooling est définie, alors il remplace celui info du package
        if 'advanced' in data and 'spooling' in data['advanced'] :
            prioritylist = ["high", "ordinary"]
            if data['advanced']['spooling'] in prioritylist :
                #limit_rate_ko in avansed deploy
                data['descriptor']['info']['spooling']= str(data['advanced']['spooling'])
                data['advanced'].pop('spooling')
                objectxmpp.xmpplog('avanced spooling parameter applied : %s'%data['descriptor']['info']['spooling'],
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Transfert | Notify",
                                    date = None ,
                                    fromuser = data['login'],
                                    touser = "")

        # RECEPTION message deploy
        if not ('step' in data or 'differed' in data):
            # difered and if
            if message['from'] == "master@pulse/MASTER":
                objectxmpp.sessionaccumulator[sessionid] = time.time()
                # le message de deploiement provient de master
                # mettre level charge dans le if
                data['resource'] = False
                if not 'cluster' in data and len(objectxmpp.jidclusterlistrelayservers) > 0:
                    # determination de ARS qui deploy
                    data['cluster'] = strjidagent
                    logger.debug("list ARS concurent : %s"%objectxmpp.jidclusterlistrelayservers)

                    levelchoisie = objectxmpp.levelcharge['charge'] +\
                                    objectxmpp.charge_apparente_cluster[strjidagent]['charge']
                    arsselection = str(strjidagent)
                    # on clear toutes les charges apparentes de plud de 5 seconde
                    for ars in objectxmpp.jidclusterlistrelayservers:
                        if not ars in objectxmpp.charge_apparente_cluster:
                            add_chargeapparente(objectxmpp, ars)
                        charge = objectxmpp.jidclusterlistrelayservers[ars]['chargenumber'] +\
                                 objectxmpp.charge_apparente_cluster[ars]['charge']
                        if charge < levelchoisie :
                            levelchoisie = objectxmpp.jidclusterlistrelayservers[ars]['chargenumber']
                            arsselection = str(ars)
                    if arsselection != strjidagent:
                        logger.debug("Charge ARS ( %s ) is %s"%(strjidagent, objectxmpp.levelcharge['charge']))
                        ###if (arsselection
                        logger.debug("DISPACHE VERS AUTRE ARS POUR LE DEPLOIEMENT : %s (charge level distant is : %s) "%(arsselection, levelchoisie) )
                    ## modify descriptor for new ARS
                    data['jidrelay'] = str(arsselection)
                    data['iprelay'] = objectxmpp.infomain['packageserver']['public_ip']
                    data['descriptor']['jidrelay'] = str(arsselection)
                    data['descriptor']['iprelay'] = objectxmpp.infomain['packageserver']['public_ip']
                    data['descriptor']['portpackageserver'] = objectxmpp.infomain['packageserver']['port']
                    data['ippackageserver'] = objectxmpp.infomain['packageserver']['public_ip']
                    data['portpackageserver'] = objectxmpp.infomain['packageserver']['port']
                    # prepare msg pour ARS choisie pour faire le deployment avec nouveau descripteur
                    datasend = {
                                    'action':  action,
                                    'sessionid' : sessionid,
                                    'data' : data,
                                    'ret' : 0,
                                    'base64' : False
                    }
                    objectxmpp.send_message( mto   = arsselection,
                                            mbody = json.dumps(datasend),
                                            mtype = 'chat')

                    if not arsselection in objectxmpp.charge_apparente_cluster:
                        add_chargeapparente(objectxmpp, arsselection)
                    q=time.time()
                    clear_chargeapparente(objectxmpp)
                    objectxmpp.charge_apparente_cluster[arsselection]['charge'] +=1
                    objectxmpp.charge_apparente_cluster[arsselection]['time'] = q
                    return
                else:
                    if not 'cluster' in data:
                        data['cluster'] = strjidagent
                        data['resource'] = False

            if 'cluster' in data and data['cluster'] != strjidagent:
                logger.debug("Cluster [(ARS %s) Delegate to deploy on (ARS %s)]"%(data['cluster'],  strjidagent) )
                #waitt master log start deploy
                time.sleep(2)
                objectxmpp.xmpplog('Cluster (ARS %s) Delegate to deploy on (ARS %s)'%(data['cluster'],strjidagent),
                                        type = 'deploy',
                                        sessionname = sessionid,
                                        priority = -1,
                                        action = "",
                                        who = strjidagent,
                                        how = "",
                                        why = "",
                                        module = "Deployment | Cluster | Notify",
                                        date = None ,
                                        fromuser = data['login'],
                                        touser = "")
            try:
                if not objectxmpp.session.isexist(sessionid):
                    logger.debug("creation session %s"%sessionid)
                    data['pushinit'] = False
                    objectxmpp.session.createsessiondatainfo(sessionid,  datasession = data, timevalid = 180)

                q=time.time()
                #on considere 10 seconde les input de deployement for premettre au ressource d etre prise
                for sesssionindex in objectxmpp.sessionaccumulator.copy():
                    if (q-objectxmpp.sessionaccumulator[sesssionindex])>10:
                        del objectxmpp.sessionaccumulator[sesssionindex]

                if len(objectxmpp.sessionaccumulator) > objectxmpp.config.concurrentdeployments or \
                   len(objectxmpp.levelcharge['machinelist']) > objectxmpp.config.concurrentdeployments:
                    maxval = maximum(len(objectxmpp.levelcharge['machinelist']),len(objectxmpp.sessionaccumulator)) 
                    objectxmpp.xmpplog("<span style='color: Orange;'>"\
                        "Spooling resource %s > concurent %s</span>"%(maxval,
                                                                      objectxmpp.config.concurrentdeployments),
                                                                      type = 'deploy',
                                                                      sessionname = sessionid,
                                                                      priority = -1,
                                                                      action = "",
                                                                      who = strjidagent,
                                                                      how = "",
                                                                      why = "",
                                                                      module = "Deployment | Transfert | Notify",
                                                                      date = None ,
                                                                      fromuser = data['login'],
                                                                      touser = "")
                    data["differed"] = True
                    data["sessionid"] = sessionid
                    data["action"] = action
                    try:
                        del data["descriptor"]["metaparameter"]
                    except  Exception as e:
                        logger.warning(str(e))
                        traceback.print_exc(file=sys.stdout)
                    msglevelspoolig =  '<span style="color: Orange;">spooling the deployment in fifo '
                    if 'spooling' in data["descriptor"]["info"]\
                        and data["descriptor"]["info"]['spooling'] == 'high':
                        objectxmpp.managefifo.setfifo(data, 'high')
                        msglevelspoolig = '%s (high priority session %s)</span>'%(msglevelspoolig, sessionid)
                    else:
                        objectxmpp.managefifo.setfifo(data)
                        msglevelspoolig = '%s (ordinary priority session %s)</span>'%(msglevelspoolig, sessionid)
                    objectxmpp.xmpplog(msglevelspoolig,
                                        type = 'deploy',
                                        sessionname = sessionid,
                                        priority = -1,
                                        action = "",
                                        who = strjidagent,
                                        how = "",
                                        why = "",
                                        module = "Deployment | Transfert | Notify",
                                        date = None ,
                                        fromuser = data['login'],
                                        touser = "")
                    return
            except Exception as e:
                logger.debug("error setfifo : %s"%str(e))
                logger.error("\n%s"%(traceback.format_exc()))
                # if not return deploy continue
                return

        # Start deploiement
        if 'differed' in data:
            removeresource(data, objectxmpp, sessionid)
            objectxmpp.xmpplog( 'launch the %s deployment in spooling mode'%sessionid,
                                type = 'deploy',
                                sessionname = sessionid,
                                priority = -1,
                                action = "",
                                who = strjidagent,
                                how = "",
                                why = "",
                                module = "Deployment | Transfert | Notify",
                                date = None ,
                                fromuser = data['login'],
                                touser = "")
            #objectxmpp.levelcharge = objectxmpp.levelcharge - 1
        if 'advanced' in data and 'limit_rate_ko' in data['advanced'] :
            if data['advanced']['limit_rate_ko'] != 0:
                #limit_rate_ko in avansed deploy
                data['descriptor']['info']['limit_rate_ko']= str(data['advanced']['limit_rate_ko'])
                objectxmpp.xmpplog('limite rade avanced deploy : %s'%data['descriptor']['info']['limit_rate_ko'],
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Transfert | Notify",
                                    date = None ,
                                    fromuser = data['login'],
                                    touser = "")
        #determine methode transfert
        if 'descriptor' in data and 'info' in data['descriptor'] and 'methodetransfert' in data['descriptor']['info']:
            data['methodetransfert'] = data['descriptor']['info']['methodetransfert']
        if 'descriptor' in data and 'info' in data['descriptor'] and 'limit_rate_ko' in data['descriptor']['info']:
            data['limit_rate_ko'] = data['descriptor']['info']['limit_rate_ko']


        if 'transfert' in data:
            if data['transfert'] == True:
                objectxmpp.xmpplog('file transfert is enabled',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Transfert | Notify",
                                    date = None ,
                                    fromuser = data['login'],
                                    touser = "")
                if 'methodetransfert' in data:
                    objectxmpp.xmpplog('Transfert Method is %s'%data['methodetransfert'],
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Transfert | Notify",
                                    date = None ,
                                    fromuser = data['login'],
                                    touser = "")
            else:
                objectxmpp.xmpplog('File transfer is disabled',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = strjidagent,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Transfert | Notify",
                                    date = None ,
                                    fromuser = data['login'],
                                    touser = "")
            #verify if possible methode of transfert.
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            try:
                sock.connect((data['ipmachine'], Globaldata['port_local']))
            except socket.error:
                if 'transfert' in data  and data['transfert'] == True \
                        and 'methodetransfert' in data \
                            and not data['methodetransfert'] in ["pullcurl",  "pullrsync", "pullscp"]:
                    try:
                        if objectxmpp.config.pushsubstitutionmethod in ["pullcurl",  "pullrsync", "pullscp"]:
                            data['methodetransfert'] = objectxmpp.config.pushsubstitutionmethod
                        else:
                            data['methodetransfert'] = "pullrsync"
                            logger.warning("check typo parameters pushsubstitutionmethod")
                    except:
                        logger.warning("check parameters pushsubstitutionmethod")
                        data['methodetransfert'] = "pullrsync"
                    objectxmpp.xmpplog('Warning push methode impossible for machine nat: force %s method'%data['methodetransfert'],
                                        type = 'deploy',
                                        sessionname = sessionid,
                                        priority = -1,
                                        action = "",
                                        who = strjidagent,
                                        how = "",
                                        why = "",
                                        module = "Deployment | Transfert | Notify",
                                        date = None ,
                                        fromuser = data['login'],
                                        touser = "")
            finally:
                sock.close()
        if 'transfert' in data \
            and data['transfert'] == True\
                and 'methodetransfert' in data\
                    and data['methodetransfert'] in ["pullcurl"]:
            transfertdeploy = { 'action': action,
                                'sessionid': sessionid,
                                'data' : data,
                                'ret' : 0,
                                'base64' : False }

            objectxmpp.send_message( mto = data['jidmachine'],
                                     mbody = json.dumps(transfertdeploy),
                                     mtype = 'chat')
            if not objectxmpp.session.isexist(sessionid):
                logger.debug("creation session %s"%sessionid)
                objectxmpp.session.createsessiondatainfo(sessionid,  datasession = transfertdeploy, timevalid = 180)
            return

        if 'transfert' in data \
            and data['transfert'] == True\
                and 'methodetransfert' in data\
                    and data['methodetransfert'] in ["pullrsync", "pullscp"] \
                        and not 'transfertpullrsync' in data:
            data['transfertpullrsync'] = True
            # creation d'un reverce ssh
            # pour avoir 1 canal de transfert.
            #remoteport = randint(49152, 65535)
            remoteport = get_free_tcp_port()
            data['remoteport'] = remoteport
            datareversessh = {  'action': 'reverse_ssh_on',
                                'sessionid': sessionid,
                                'data' : { 'request' : 'askinfo',
                                            'port' : remoteport,
                                            'host' : data['uuid'],
                                            'remoteport' :  Globaldata['port_local'],
                                            'reversetype' : 'R',
                                            'options' : 'createreversessh',
                                            'persistance' : 'no' },
                                'ret' : 0,
                                'base64' : False }
            objectxmpp.send_message(mto = message['to'],
                                    mbody = json.dumps(datareversessh),
                                    mtype = 'chat')
            objectxmpp.xmpplog('creation reverse ssh remote (port %s->%s) from %s'%(Globaldata['port_local'],
                                                                                    remoteport,
                                                                                    str(objectxmpp.boundjid.bare)),
                                type = 'deploy',
                                sessionname = sessionid,
                                priority = -1,
                                action = "",
                                who = strjidagent,
                                how = "",
                                why = "",
                                module = "Deployment | Transfert | Notify",
                                date = None ,
                                fromuser = data['login'],
                                touser = "")
            time.sleep(2)
            #logger.debug("Install key ARS in authorized_keys on agent machine %s"%data['jidmachine'])
            #body = {'action' : 'installkey',
                    #'sessionid': sessionid,
                    #'data' : { 'jidAM' : data['jidmachine']
                    #}
            #}
            #objectxmpp.send_message(  mto = strjidagent,
                                      #mbody = json.dumps(body),
                                      #mtype = 'chat')
            time.sleep(6)
        ########################################################
        #traitement mode push et les mode "pullrsync", "pullscp"
        ########################################################

        # mode push ARS to AM
        # UPLOAD FILE PACKAGE to MACHINE, all dependency
        # We are in the case where it is necessary to install all the packages for the deployment, dependency included
        if ('pushinit' in data and data['pushinit'] == False)  or not objectxmpp.session.isexist(sessionid):
            data['pushinit'] = True
            objectxmpp.session.createsessiondatainfo(sessionid,  datasession = data, timevalid = 180)
            if 'methodetransfert' in data and data['methodetransfert'] == "pushrsync":
                # installkey sur agent machine authorized_keys
                logger.debug("Install key ARS in authorized_keys on agent machine")
                body = {'action' : 'installkey',
                        'sessionid': sessionid,
                        'data' : { 'jidAM' : data['jidmachine']
                        }
                }
                objectxmpp.send_message(  mto = strjidagent,
                                            mbody = json.dumps(body),
                                            mtype = 'chat')
                # give time to apply the key
                time.sleep(8)
            ## In push method you must know or install the packages on machine agent
            ## In push mode, the packets are sent to a location depending on reception
            ## one must make a request to AM to know or sent the files.
            ## request message pacquage location
            ## create a message with the deploy sessionid.
            ## action will be a call to a plugin info request here the folder_packages
            ## le resultat de cet appel est un appel a plugin_applicationdeploymentjson.py avec meme sessionid et info du directory
            #logger.debug("search directory pakage flolder from AM")
            askinfo( data['jidmachine'],
                    sessionid,
                    objectxmpp,
                    informationasking = ['folders_packages', 'os', 'cpu_arch'],
                    replyaction = action)
        else:
            # The session exists

            logger.debug("LA SESSION EXISTE")
            objsession = objectxmpp.session.sessionfromsessiondata(sessionid)
            data_in_session = objsession.getdatasession()

            if 'step' not in data:
                logger.debug("STEP NOT")
                #if 'keyinstall' in data and data['keyinstall'] == True:
                    ## We manage the message condition installation key
                    #logger.debug("keyinstall in true")
                    #data_in_session['keyinstall'] = True
                    #objsession.setdatasession(data_in_session)

                if 'actiontype' in data and data['actiontype'] == 'requestinfo' :
                    if 'folders_packages' in data :
                        data_in_session['folders_packages'] = data['folders_packages']
                        logger.debug("folders_packages client machine %s"%data_in_session['folders_packages'])
                    if 'cpu_arch' in data:
                        data_in_session['cpu_arch'] = data['cpu_arch']
                        logger.debug("cpu architecture client machine %s"%data_in_session['cpu_arch'])
                    if 'os' in data:
                        data_in_session['os'] = data['os']
                        logger.debug("os client machine %s"%data_in_session['os'])
                        data_in_session['os_version'] = data['os_version']
                        #set  user ssh
                        data_in_session['userssh'] = "pulseuser"
                        if data_in_session['os'].startswith('linux'):
                            data_in_session['rsyncpath'] = "rsync"
                        elif data_in_session['os'].startswith('win'):
                            if data_in_session['cpu_arch'].endswith('64'):
                                data_in_session['rsyncpath'] = "C:\\\\Windows\\\\SysWOW64\\\\rsync.exe"
                            else:
                                data_in_session['rsyncpath'] = "C:\\\\Windows\\\\System32\\\\rsync.exe"
                        elif data_in_session['os'].startswith('darwin'):
                            data_in_session['rsyncpath'] = "rsync"
                    # information set in session data
                    objsession.setdatasession(data_in_session)

                # We verify that we have all the information for the deployment
                if not 'folders_packages' in data_in_session or not 'os' in data_in_session:
                    # termine deploy on error
                    # We do not know folders_packages
                    logger.debug("SORRY DEPLOY TERMINATE FOLDERS_PACKAGE MISSING")
                    objectxmpp.xmpplog('<span style="color: red;";>[xxx]: Terminate deploy ERROR folders_packages %s missing</span>',
                                type = 'deploy',
                                sessionname = sessionid,
                                priority = 0,
                                action = "",
                                who = strjidagent,
                                how = "",
                                why = "",
                                module = "Deployment | Error",
                                date = None ,
                                fromuser = data_in_session['name'],
                                touser = "")
                    #termine session a tester

                    data_in_session['environ'] = {}
                    cleandescriptor( data_in_session )
                    datalog = {
                        'action' : "result%s"%action,
                        'sessionid': sessionid,
                        'ret' : 255,
                        'base64' : False,
                        'data' : data_in_session
                    }

                    objectxmpp.send_message(mto='log@pulse',
                                            mbody=json.dumps(datalog),
                                            mtype='chat')
                    objectxmpp.send_message(mto="master@pulse/MASTER",
                                            mbody=json.dumps(datalog),
                                            mtype='chat')
                    #termine session a tester
                    #clean session
                    if objectxmpp.session.isexist(sessionid):
                        objectxmpp.session.clearnoevent(sessionid)
                    return

                    #if not 'folders_packages' in data_in_session or not 'keyinstall' in data_in_session:
                if not 'folders_packages' in data_in_session:
                    # If the 2 conditions are not yet satisfied:
                    # - Key public ARS installed on AM,
                    # - And return the path or install the packages.
                    # We leave and await message of the missing condition.
                    return

                # We have all the information we continue deploy
                # You have to prepare the transfer of packages.
                # You must have a list of all the packages to install.
                # Because pakages can have dependencies

                list_of_deployment_packages = search_list_of_deployment_packages(data_in_session['path'].split('/')[-1]).search()
                #Install packages
                #logger.debug("#################LIST PACKAGE DEPLOY SESSION #######################")
                # saves the list of packages to be transferred in the session.
                data_in_session['transferfiles'] = [x for x in list(list_of_deployment_packages) if x != ""]
                objsession.setdatasession(data_in_session)
                ### this plugin will call itself itself is transfer each time a package from the list of packages to transfer.
                ### to make this call we prepare a message with the current session.
                ### on the message ['step'] of the message or resume processing.
                ### here data ['step'] = "transferfiles"
                logger.debug("APPEL POUR PHASE DE TRANSFERTS" )
                # call for aller step suivant transfert file
                msg_self_call = create_message_self_for_transfertfile(sessionid)
                objectxmpp.send_message(mto = strjidagent,
                                        mbody = json.dumps(msg_self_call),
                                        mtype = 'chat')
            else:
                ########## session transfer file ##########
                #analysis of the resume variable (step)
                if data['step'] == "transferfiles":
                    logger.debug("SESSION TRANSFERT PACKAGES" )
                    #logger.debug("DATA est %s"%json.dumps(data, indent = 4) )

                    if 'transferfiles' in data_in_session and len ( data_in_session['transferfiles']) != 0:
                        uuidpackages = data_in_session['transferfiles'].pop(0)
                        pathin = managepackage.getpathpackage(uuidpackages)
                        #This variable will be in the future used for the transferrt version of rsync files
                        #pathout = "%s/%s"%(data_in_session['folders_packages'],pathin.split('/')[-1])
                        # Update the session for the next call.
                        # The transferred package is excluded from the list of future packages to install
                        objsession.setdatasession(data_in_session)
                        logger.debug("SEND COMMANDE")
                        logger.debug("TRANSFERT PACKAGE from %s"%pathin)
                        #The rsync command will have this form
                        packuuid = os.path.basename(pathin)
                        if 'limit_rate_ko' in data_in_session and \
                            data_in_session['limit_rate_ko'] != "" and\
                                int(data_in_session['limit_rate_ko']) > 0:
                            cmdpre = "scp -C -r -l %s "%(int(data_in_session['limit_rate_ko']) * 8)
                            cmdrsync = "rsync -z --rsync-path=%s --bwlimit=%s "%(data_in_session['rsyncpath'],
                                                                                 int(data_in_session['limit_rate_ko']) * 8)

                            msg = "rsync transfert package :%s to %s <span style='font-weight: "\
                                "bold;color : orange;'> [transfert rate %s ko]</span>"%(data_in_session['name'],
                                                                                        data_in_session['jidmachine'], 
                                                                                        data_in_session['limit_rate_ko'])
                        else:
                            cmdpre = "scp -C -r "
                            cmdrsync = "rsync -z --rsync-path=%s "%data_in_session['rsyncpath']
                            msg = "scp transfert package :%s to %s"%(data_in_session['name'],data_in_session['jidmachine'])

                        ipmachine = data_in_session['ipmachine']
                        if not 'remoteport' in data_in_session:
                            clientssshport = Globaldata['port_local']
                        else :
                            clientssshport = data_in_session['remoteport']
                            ipmachine = "localhost"

                        optionscp = "-o IdentityFile=/root/.ssh/id_rsa "\
                                    "-o StrictHostKeyChecking=no "\
                                    "-o UserKnownHostsFile=/dev/null "\
                                    "-o Batchmode=yes "\
                                    "-o PasswordAuthentication=no "\
                                    "-o ServerAliveInterval=10 "\
                                    "-o CheckHostIP=no "\
                                    "-o LogLevel=ERROR "\
                                    "-o ConnectTimeout=10 "\
                                    "-o Port=%s "\
                                    "%s %s@%s:\"\\\"%s\\\"\""%( clientssshport,
                                                    pathin,
                                                    data_in_session['userssh'],
                                                    ipmachine,
                                                    data_in_session['folders_packages'])

                        if data_in_session['folders_packages'].lower().startswith('c:') or data_in_session['folders_packages'][1] == ":" :
                            pathnew =  data_in_session['folders_packages'][2:]
                            # cywin path
                            pathnew = "/cygdrive/c/" + pathnew.replace("\\","/") + "/" + packuuid + "/"
                            #compose name for rsync
                            listpath = pathnew.split("/")
                            p = []
                            for indexpath in listpath:
                                if " " in indexpath:
                                    p.append('"' + indexpath + '"')
                                else:
                                    p.append(indexpath)
                            pathnew = "/".join(p)
                        else:
                            pathnew = data_in_session['folders_packages'] + "/" + packuuid + "/"
                        pathnew = pathnew.replace("//","/")
                        optionrsync = " -e \"ssh -o IdentityFile=/root/.ssh/id_rsa "\
                                        "-o UserKnownHostsFile=/dev/null "\
                                        "-o StrictHostKeyChecking=no "\
                                        "-o Batchmode=yes "\
                                        "-o PasswordAuthentication=no "\
                                        "-o ServerAliveInterval=10 "\
                                        "-o CheckHostIP=no "\
                                        "-o LogLevel=ERROR "\
                                        "-o ConnectTimeout=10 "\
                                        "-o Port=%s\" "\
                                        "-av --chmod=777 %s/ %s@%s:'%s'"%( clientssshport,
                                                            pathin,
                                                            data_in_session['userssh'],
                                                            ipmachine,
                                                            pathnew)
                        cmdscp = cmdpre + optionscp
                        cmdrsync = cmdrsync + optionrsync

                        if not os.path.isdir(data_in_session['path']):
                            objectxmpp.xmpplog('<span style="color: red;";>ERROR transfert [Package Server does not have this package %s]</span>'%data_in_session['path'],
                                            type = 'deploy',
                                            sessionname = sessionid,
                                            priority = -1,
                                            action = "",
                                            who = strjidagent,
                                            how = "",
                                            why = "",
                                            module = "Deployment | Error | Download | Transfert",
                                            date = None ,
                                            fromuser = data_in_session['login'],
                                            touser = "")
                            objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                type = 'deploy',
                                sessionname = sessionid,
                                priority = -1,
                                action = "",
                                who = strjidagent,
                                how = "",
                                why = "",
                                module = "Deployment | Terminate |Notify",
                                date = None ,
                                fromuser = "AM %s"% strjidagent,
                                touser = "")
                            data_in_session['environ'] = {}
                            cleandescriptor( data_in_session )
                            datalog = {
                                'action' : "result%s"%action,
                                'sessionid': sessionid,
                                'ret' : 255,
                                'base64' : False,
                                'data' : data_in_session
                            }

                            objectxmpp.send_message(mto='log@pulse',
                                                    mbody=json.dumps(datalog),
                                                    mtype='chat')
                            objectxmpp.send_message(mto="master@pulse/MASTER",
                                                    mbody=json.dumps(datalog),
                                                    mtype='chat')
                            #termine session a tester
                            #clean session
                            if objectxmpp.session.isexist(sessionid):
                                objectxmpp.session.clearnoevent(sessionid)
                            return
                        #push transfert
                        try:
                            takeresource(data_in_session, objectxmpp, sessionid)
                            if hasattr(objectxmpp.config, 'pushmethod') and objectxmpp.config.pushmethod == "scp":
                                cmdexec = cmdscp
                            else:
                                objectxmpp.config.pushmethod = "rsync"
                                cmdexec = cmdrsync
                            logger.debug("tranfert cmd :\n %s"%cmdexec)
                            objectxmpp.xmpplog( "cmd : <span style=\"font-weight: bold;font-style: italic; color: blue;\">" + cmdexec + "</span>",
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = strjidagent,
                                                how = "",
                                                why = "",
                                                module = "Deployment | Error | Download | Transfert",
                                                date = None ,
                                                fromuser = data_in_session['login'],
                                                touser = "")
                            obcmd = simplecommandstr(cmdexec)
                            if obcmd['code'] != 0:
                                objectxmpp.xmpplog('<span style="color: red;";>[xxx]:  %s deploy ERROR transfert %s </span>'%(objectxmpp.config.pushmethod,
                                                                                                                            obcmd['result']),
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = strjidagent,
                                                how = "",
                                                why = "",
                                                module = "Deployment | Error | Download | Transfert",
                                                date = None ,
                                                fromuser = data_in_session['login'],
                                                touser = "")
                                cmdexec = cmdexec.replace("pulseuser","pulse")
                                objectxmpp.xmpplog( "cmd : <span style=\"font-weight: bold;font-style: italic; color: blue;\">" + cmdexec + "</span>",
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = strjidagent,
                                                how = "",
                                                why = "",
                                                module = "Deployment | Error | Download | Transfert",
                                                date = None ,
                                                fromuser = data_in_session['login'],
                                                touser = "")
                                obcmd = simplecommandstr(cmdexec)
                            objectxmpp.xmpplog( msg,
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = strjidagent,
                                                how = "",
                                                why = "",
                                                module = "Deployment | Error | Download | Transfert",
                                                date = None ,
                                                fromuser = data_in_session['login'],
                                                touser = "")
                        finally:
                            time.sleep(2)
                            removeresource(data_in_session, objectxmpp, sessionid)

                        if obcmd['code'] != 0:
                            objectxmpp.xmpplog('<span style="color: red;";>[xxx]: Terminate %s deploy ERROR transfert %s </span>'%(objectxmpp.config.pushmethod,obcmd['result']),
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = strjidagent,
                                                how = "",
                                                why = "",
                                                module = "Deployment | Error | Download | Transfert",
                                                date = None ,
                                                fromuser = data_in_session['login'],
                                                touser = "")
                            objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = strjidagent,
                                                how = "",
                                                why = "",
                                                module = "Deployment | Terminate |Notify",
                                                date = None ,
                                                fromuser = "AM %s"% strjidagent,
                                                touser = "")
                            data_in_session['environ'] = {}
                            cleandescriptor( data_in_session )
                            datalog = {
                                'action' : "result%s"%action,
                                'sessionid': sessionid,
                                'ret' : 255,
                                'base64' : False,
                                'data' : data_in_session
                            }

                            objectxmpp.send_message(mto='log@pulse',
                                                    mbody=json.dumps(datalog),
                                                    mtype='chat')
                            objectxmpp.send_message(mto="master@pulse/MASTER",
                                                    mbody=json.dumps(datalog),
                                                    mtype='chat')
                            #termine session a tester
                            #clean session
                            if objectxmpp.session.isexist(sessionid):
                                objectxmpp.session.clearnoevent(sessionid)
                            return
                        else:
                            objectxmpp.xmpplog('Result : %s'\
                                               '\nTransfert <span style="color:'\
                                               ' blue;">%s </span>'%(objectxmpp.config.pushmethod,
                                                                     obcmd['result']),
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = strjidagent,
                                                how = "",
                                                why = "",
                                                module = "Deployment | Terminate |Notify",
                                                date = None ,
                                                fromuser = "ARS %s"% strjidagent,
                                                touser = "")
                        logger.debug("CALL FOR NEXT PACKAGE")
                        # call for aller step suivant
                        objectxmpp.send_message(mto = strjidagent,
                                            mbody = json.dumps(create_message_self_for_transfertfile(sessionid)),
                                            mtype = 'chat')
                    else:
                        ##uninstall keypublic on machine after transfert package
                        #keypublic = get_keypub_ssh()
                        #uninstallkeypub = {
                                            #'action': "setkeypubliconauthorizedkeys",
                                            #'sessionid': sessionid,
                                            #'data' : {'keypub' : keypublic, 'install' : False},
                                            #'ret' : 0,
                                            #'base64' : False }
                        #objectxmpp.send_message(mto = data_in_session['jidmachine'],
                                            #mbody = json.dumps(uninstallkeypub),
                                            #mtype = 'chat')
                        # Creation of the message from depoy to machine
                        logger.debug("APPEL PLUGIN FOR DEPLOY ON MACHINE")
                        transfertdeploy = {
                                            'action': action,
                                            'sessionid': sessionid,
                                            'data' : data_in_session,
                                            'ret' : 0,
                                            'base64' : False }
                        #logger.debug(json.dumps(transfertdeploy, indent = 4))
                        objectxmpp.send_message(mto = data_in_session['jidmachine'],
                                mbody = json.dumps(transfertdeploy),
                                mtype = 'chat')
                        #transfert terminer update Has_login_command
                        datasend = {
                                    'action':  "updatenbdeploy",
                                    'sessionid' : sessionid,
                                    'data' : data_in_session['advanced'],
                                    'ret' : 1,
                                    'base64' : False
                                }
                        objectxmpp.send_message(mto=data_in_session['jidmaster'],
                                                mbody = json.dumps(datasend),
                                                mtype = 'chat')
                        if objectxmpp.session.isexist(sessionid):
                            objectxmpp.session.clearnoevent(sessionid)
