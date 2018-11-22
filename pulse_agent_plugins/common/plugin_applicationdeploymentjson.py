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
#from lib.utils import save_back_to_deploy, cleanbacktodeploy, simplecommandstr, get_keypub_ssh
from lib.utils import save_back_to_deploy, cleanbacktodeploy, simplecommandstr, isBase64
import copy
import traceback
from sleekxmpp.xmlstream import  JID
import time
logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25

plugin = {"VERSION" : "3.07", "NAME" : "applicationdeploymentjson", "TYPE" : "all"}


"""
Plugin for deploying a package
"""

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
    jidrs = JID(datasendl['data']['jidrelay'])
    jidr = "%s@%s"%(jidrs.user, jidrs.domain) 
    if jidr != objectxmpp.boundjid.bare:
        # libere la resources sur ARS par message (rend 1 resource)
        msgresource = {'action': "cluster",
                       'sessionid': sessionid,
                       'data' :  {"subaction" : "takeresource",
                                  "data" : {'user' : datasendl['data']['advanced']['login']}},
                       'ret' : 0,
                       'base64' : False}
        objectxmpp.send_message(mto = datasendl['data']['jidrelay'],
                                mbody = json.dumps(msgresource),
                                mtype = 'chat')
#    else:
#        resource = objectxmpp.checklevelcharge(1)
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
    jidrs = JID(datasendl['data']['jidrelay'])
    jidr = "%s@%s"%(jidrs.user, jidrs.domain)
    if jidr != objectxmpp.boundjid.bare:
        # libere la resources sur ARS par message (rend 1 resource)
        msgresource = {'action': "cluster",
                       'sessionid': sessionid,
                       'data' :  { "subaction" : "removeresource", "data" : {'user' : datasendl['data']['advanced']['login']}},
                       'ret' : 0,
                       'base64' : False}
        objectxmpp.send_message(mto = datasendl['data']['jidrelay'],
                                mbody = json.dumps(msgresource),
                                mtype = 'chat')
#    else :
#        resource = objectxmpp.checklevelcharge(-1)
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
                        who = objectxmpp.boundjid.bare,
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
                                who = objectxmpp.boundjid.bare,
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

def recuperefile(datasend, objectxmpp, ippackage, portpackage, sessionid):
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
                       who = objectxmpp.boundjid.bare,
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

            #logger.debug("###################################################")
            #logger.debug("adress telechargement package par le client en curl : " + urlfile)
            #logger.debug("###################################################")
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
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Download | Transfert",
                                    date = None ,
                                    fromuser = datasend['data']['advanced']['login'],
                                    touser = "")
                curlgetdownloadfile( dest, urlfile, insecure = True, limit_rate_ko = limit_rate_ko)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                logger.debug(str(e))
                objectxmpp.xmpplog('<span style="font-weight: bold;color : red;">STOP DEPLOY ON ERROR : download curl [%s] file package : %s</span>'%(curlurlbase, filepackage),
                                    type = 'deploy',
                                    sessionname = datasend['sessionid'],
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Error  | Notify | Execution",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
                                    touser = "")
                    objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate |Notify",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Error | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
                                    touser = "")
                objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Error | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
                                    touser = "")
                objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
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
                                who = objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
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
                                who = objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Error",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
                                    touser = "")
                    if sessionid in objectxmpp.back_to_deploy:
                        objectxmpp.xmpplog('<span style="font-weight: bold;color : red;">List of abandoned dependencies %s</span>'%objectxmpp.back_to_deploy[sessionid]['Dependency'],
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Dependencies | Transfert | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
                                    touser = "")
                    objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
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
                                        who = objectxmpp.boundjid.bare,
                                        how = "",
                                        why = "",
                                        module = "Deployment | Dependency",
                                        date = None ,
                                        fromuser = "AM %s"% objectxmpp.boundjid.bare,
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
                                        who = objectxmpp.boundjid.bare,
                                        how = "",
                                        why = "",
                                        module = "Deployment | Dependency",
                                        date = None ,
                                        fromuser = "AM %s"% objectxmpp.boundjid.bare,
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
                                        who = objectxmpp.boundjid.bare,
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
                                        #who = objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
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
            if data['methodetransfert'] == "pullcurl" and data['transfert'] :
                #pull method download file
                #takeresource(datasend, objectxmpp, sessionid)
                recupfile = recuperefile(datasend, objectxmpp,  data['ippackageserver'], data['portpackageserver'], sessionid)
                #removeresource(datasend, objectxmpp, sessionid)
                if not recupfile:
                    logger.debug("Error curl")
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
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate | Notify",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
                                    touser = "")
                    signalendsessionforARS(data , objectxmpp, sessionid, error = True)

                    # termine sesion on error
                    # clean session
                    objectxmpp.session.clearnoevent(sessionid)
                    # clean if not session
                    cleanbacktodeploy(objectxmpp)
                    return
                else:
                    # Pull transfer complete
                    # send message to master for updatenbdeploy
                    datasend1 = {
                                'action':  "updatenbdeploy",
                                'sessionid' : sessionid,
                                'data' : data['advanced'],
                                'ret' : 1,
                                'base64' : False
                    }
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
                                    who = objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
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
                # le message de deploiement provient de master
                # mettre level charge dans le if
                data['resource'] = False
                if not 'cluster' in data and len(objectxmpp.jidclusterlistrelayservers) > 0:
                    # determination de ARS qui deploy

                    data['cluster'] = objectxmpp.boundjid.bare
                    logger.debug("list ARS concurent : %s"%objectxmpp.jidclusterlistrelayservers)

                    levelchoisie = objectxmpp.levelcharge
                    arsselection = objectxmpp.boundjid.bare
                    for ars in objectxmpp.jidclusterlistrelayservers:
                        if objectxmpp.jidclusterlistrelayservers[ars]['chargenumber'] < levelchoisie :
                            levelchoisie = objectxmpp.jidclusterlistrelayservers[ars]['chargenumber']
                            arsselection = ars

                    if arsselection != objectxmpp.boundjid.bare:
                        logger.debug("Charge ARS ( %s ) is %s"%(objectxmpp.boundjid.bare, objectxmpp.levelcharge))
                        ###if (arsselection
                        logger.debug("DISPACHE VERS AUTRE ARS POUR LE DEPLOIEMENT : %s (charge level : %s) "%(arsselection, levelchoisie) )
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
                    return
                else:
                    if not 'cluster' in data:
                        data['cluster'] = objectxmpp.boundjid.bare
                        data['resource'] = False

            if 'cluster' in data and data['cluster'] != objectxmpp.boundjid.bare:
                logger.debug("DEPLOIEMENT : ARS %s DISPACHE TO  ARS %s "%(data['cluster'], objectxmpp.boundjid.bare ) )
                #waitt master log start deploy
                time.sleep(2)
                objectxmpp.xmpplog('Cluster (ARS %s) Delegate to deploy on (ARS %s)'%(data['cluster'],objectxmpp.boundjid.bare),
                                        type = 'deploy',
                                        sessionname = sessionid,
                                        priority = -1,
                                        action = "",
                                        who = objectxmpp.boundjid.bare,
                                        how = "",
                                        why = "",
                                        module = "Deployment | Cluster | Notify",
                                        date = None ,
                                        fromuser = data['login'],
                                        touser = "")

            try:
                objectxmpp.xmpplog("Spooling resource %s > concurent %s"%(len(objectxmpp.session.resource), objectxmpp.config.concurrentdeployments),
                                            type = 'deploy',
                                            sessionname = sessionid,
                                            priority = -1,
                                            action = "",
                                            who = objectxmpp.boundjid.bare,
                                            how = "",
                                            why = "",
                                            module = "Deployment | Transfert | Notify",
                                            date = None ,
                                            fromuser = data['login'],
                                            touser = "")
 
                objectxmpp.session.resource.add(sessionid)
                if not objectxmpp.session.isexist(sessionid):
                    logger.debug("creation session %s"%sessionid)
                    data['pushinit'] = False
                    objectxmpp.session.createsessiondatainfo(sessionid,  datasession = data, timevalid = 180)
                if len(objectxmpp.session.resource) > objectxmpp.config.concurrentdeployments:
                    objectxmpp.levelcharge = objectxmpp.levelcharge + 1

                    data["differed"] = True
                    data["sessionid"] = sessionid
                    data["action"] = action
                    try:
                        del data["descriptor"]["metaparameter"]
                    except  Exception as e:
                        logger.warning(str(e))
                        traceback.print_exc(file=sys.stdout)
                    msglevelspoolig = ""
                    if 'spooling' in data["descriptor"]["info"]\
                        and data["descriptor"]["info"]['spooling'] == 'high':
                        objectxmpp.managefifo.setfifo(data, 'high')
                        msglevelspoolig = 'spooling the deployment %s (high priority)'%sessionid
                    else:
                        objectxmpp.managefifo.setfifo(data)
                        msglevelspoolig = 'spooling the deployment %s (ordinary priority)'%sessionid
                    if msglevelspoolig != "":
                        objectxmpp.xmpplog(msglevelspoolig,
                                            type = 'deploy',
                                            sessionname = sessionid,
                                            priority = -1,
                                            action = "",
                                            who = objectxmpp.boundjid.bare,
                                            how = "",
                                            why = "",
                                            module = "Deployment | Transfert | Notify",
                                            date = None ,
                                            fromuser = data['login'],
                                            touser = "")
                    takeresource(data, objectxmpp, sessionid)
                    return
            except Exception as e:
                logger.debug("%s"%str(e))
                pass

        # Start deploiement
        if 'differed' in data:
            removeresource(data, objectxmpp, sessionid)
            objectxmpp.xmpplog('und spooling the deployment %s'%sessionid,
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Transfert | Notify",
                                    date = None ,
                                    fromuser = data['login'],
                                    touser = "")
            objectxmpp.levelcharge = objectxmpp.levelcharge - 1
        if 'advanced' in data and 'limit_rate_ko' in data['advanced'] :
            if data['advanced']['limit_rate_ko'] != 0:
                #limit_rate_ko in avansed deploy
                data['descriptor']['info']['limit_rate_ko']= str(data['advanced']['limit_rate_ko'])
                objectxmpp.xmpplog('limite rade avanced deploy : %s'%data['descriptor']['info']['limit_rate_ko'],
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
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
                sock.connect((data['ipmachine'], 22))
            except socket.error:
                if 'transfert' in data  and data['transfert'] == True \
                        and 'methodetransfert' in data \
                            and data['methodetransfert'] != "pullcurl":
                    data['methodetransfert'] = "pullcurl"
                    objectxmpp.xmpplog('Warning push methode impossible for machine nat: force pull curl method',
                                        type = 'deploy',
                                        sessionname = sessionid,
                                        priority = -1,
                                        action = "",
                                        who = objectxmpp.boundjid.bare,
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
                    and data['methodetransfert'] == "pullcurl":
            #mode pull AM to ARS
            ### Send deployment message directly to machine
            transfertdeploy = {
                                'action': action,
                                'sessionid': sessionid,
                                'data' : data,
                                'ret' : 0,
                                'base64' : False }
            objectxmpp.send_message(mto = data['jidmachine'],
                                    mbody = json.dumps(transfertdeploy),
                                    mtype = 'chat')
            if not objectxmpp.session.isexist(sessionid):
                logger.debug("creation session %s"%sessionid)
                objectxmpp.session.createsessiondatainfo(sessionid,  datasession = transfertdeploy, timevalid = 180)
        else:
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
                    objectxmpp.send_message(  mto = objectxmpp.boundjid.bare,
                                                mbody = json.dumps(body),
                                                mtype = 'chat')
                    # give time to apply the key
                    time.sleep(4)
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
                        informationasking = ['folders_packages'],
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

                    if 'actiontype' in data and 'folders_packages' in data and data['actiontype'] == 'requestinfo' :
                        logger.debug("folders_packages")
                        data_in_session['folders_packages'] = data['folders_packages']
                        objsession.setdatasession(data_in_session)

                    # We verify that we have all the information for the deployment
                    if 'folders_packages' in data_in_session and data_in_session['folders_packages'] == "":
                        # termine deploy on error
                        # We do not know folders_packages
                        logger.debug("SORRY DEPLOY TERMINATE FOLDERS_PACKAGE MISSING")
                        objectxmpp.xmpplog('<span style="color: red;";>[xxx]: Terminate deploy ERROR folders_packages %s missing</span>',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = 0,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
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
                    objectxmpp.send_message(mto = objectxmpp.boundjid.bare,
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
                                cmdrsyn = "rsync -z --bwlimit=%s "%(int(data_in_session['limit_rate_ko']) * 8)

                                msg = "push transfert package :%s to %s <span style='font-weight: bold;color : orange;'> [transfert rate %s ko]</span>"%(data_in_session['name'],data_in_session['jidmachine'], data_in_session['limit_rate_ko'])
                            else:
                                cmdpre = "scp -C -r "
                                cmdrsyn = "rsync -z "
                                msg = "push transfert package :%s to %s"%(data_in_session['name'],data_in_session['jidmachine'])
                            optionscp = "-o IdentityFile=/root/.ssh/id_rsa "\
                                     "-o StrictHostKeyChecking=no "\
                                     "-o UserKnownHostsFile=/dev/null "\
                                     "-o Batchmode=yes "\
                                     "-o PasswordAuthentication=no "\
                                     "-o ServerAliveInterval=10 "\
                                     "-o CheckHostIP=no "\
                                     "-o LogLevel=ERROR "\
                                     "-o ConnectTimeout=10 "\
                                        "%s %s@%s:\"\\\"%s\\\"\""%( pathin,
                                                        "pulse",
                                                        data_in_session['ipmachine'],
                                                        data_in_session['folders_packages'])

                            if data_in_session['folders_packages'].lower().startswith('c:') or data_in_session['folders_packages'][1] == ":" :
                                pathnew =  data_in_session['folders_packages'][2:]
                                pathnew = "../../../../" + pathnew.replace("\\","/") + packuuid + "/"
                            else:
                                pathnew = data_in_session['folders_packages'] + packuuid + "/"
                            pathnew = pathnew.replace("//","/")
                            optionrsync = " -e \"ssh -o IdentityFile=/root/.ssh/id_rsa "\
                                            "-o UserKnownHostsFile=/dev/null "\
                                            "-o StrictHostKeyChecking=no "\
                                            "-o Batchmode=yes "\
                                            "-o PasswordAuthentication=no "\
                                            "-o ServerAliveInterval=10 "\
                                            "-o CheckHostIP=no "\
                                            "-o LogLevel=ERROR "\
                                            "-o ConnectTimeout=10\" "\
                                            "-av %s/ %s@%s:\"%s\""%(pathin,"pulse",data_in_session['ipmachine'],pathnew)
                            cmdscp = cmdpre + optionscp
                            cmdrsyn = cmdrsyn + optionrsync

                            if not os.path.isdir(data_in_session['path']):
                                objectxmpp.xmpplog('<span style="color: red;";>ERROR transfert [Package Server does not have this package %s]</span>'%data_in_session['path'],
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = objectxmpp.boundjid.bare,
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
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Terminate |Notify",
                                    date = None ,
                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
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
                            takeresource(data_in_session, objectxmpp, sessionid)
                            if objectxmpp.config.pushmethod == "scp":
                                cmdexec = cmdscp
                            else:
                                cmdexec = cmdrsyn
                            logger.debug("tranfert cmd :\n %s"%cmdexec)
                            objectxmpp.xmpplog( "cmd : <span style=\"font-weight: bold;font-style: italic; color: blue;\">" + cmdexec + "</span>",
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = objectxmpp.boundjid.bare,
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
                                                who = objectxmpp.boundjid.bare,
                                                how = "",
                                                why = "",
                                                module = "Deployment | Error | Download | Transfert",
                                                date = None ,
                                                fromuser = data_in_session['login'],
                                                touser = "")
                            time.sleep(2)
                            removeresource(data_in_session, objectxmpp, sessionid)
                            if obcmd['code'] != 0:
                                objectxmpp.xmpplog('<span style="color: red;";>[xxx]: Terminate %s deploy ERROR transfert %s </span>'%(objectxmpp.config.pushmethod,obcmd['result']),
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = objectxmpp.boundjid.bare,
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
                                                    who = objectxmpp.boundjid.bare,
                                                    how = "",
                                                    why = "",
                                                    module = "Deployment | Terminate |Notify",
                                                    date = None ,
                                                    fromuser = "AM %s"% objectxmpp.boundjid.bare,
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
                                objectxmpp.xmpplog('Transfert %s Result : %s'%(obcmd['result'], objectxmpp.config.pushmethod),
                                                    type = 'deploy',
                                                    sessionname = sessionid,
                                                    priority = -1,
                                                    action = "",
                                                    who = objectxmpp.boundjid.bare,
                                                    how = "",
                                                    why = "",
                                                    module = "Deployment | Terminate |Notify",
                                                    date = None ,
                                                    fromuser = "ARS %s"% objectxmpp.boundjid.bare,
                                                    touser = "")
                            logger.debug("CALL FOR NEXT PACKAGE")
                            # call for aller step suivant
                            objectxmpp.send_message(mto = objectxmpp.boundjid.bare,
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
