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
import json
import sys, os
from lib.managepackage import managepackage, search_list_of_deployment_packages

from lib.grafcetdeploy import grafcet
import logging
import pycurl
import platform
from lib.utils import save_back_to_deploy, cleanbacktodeploy, simplecommandstr, get_keypub_ssh
import copy

logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25

plugin = {"VERSION" : "1.7", "NAME" : "applicationdeploymentjson", "TYPE" : "all"}


"""
Plugin for deploying a package
"""

#TQ type message query
#TR type message Reponse
#TE type message Error
#TED type message END deploy
#TEVENT remote event

def cleandescriptor( datasend ):

    if sys.platform.startswith('linux'):
        try:
            del datasend['descriptor']['win']
        except KeyError:
            pass
        try:
            del datasend['descriptor']['Macos']
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
            del datasend['descriptor']['Macos']
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
            datasend['descriptor']['sequence'] = datasend['descriptor']['Macos']['sequence']
            #del datasend['descriptor']['Macos']['sequence']
            del datasend['descriptor']['Macos']
        except:
            return False
    datasend['typeos'] = sys.platform
    return True

def create_message_self_for_transfertfile( sessionid ):
    return  {
        'action': plugin['NAME'],
        'sessionid': sessionid,
        'data' :{'step' : "transferfiles"},
        'ret' : 0,
        'base64' : False }

def askinfo(to, sessionid, objectxmpp, informationasking=[], replyaction=None, list_to_sender=[], step=None):
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

    objectxmpp.send_message( mto = to,
                             mbody = json.dumps(ask),
                             mtype = 'chat')


def curlgetdownloadfile( destfile, urlfile, insecure = True):
    # As long as the file is opened in binary mode, both Python 2 and Python 3
    # can write response body to it without decoding.
    with open(destfile, 'wb') as f:
        c = pycurl.Curl()
        c.setopt(c.URL, urlfile)
        c.setopt(c.WRITEDATA, f)
        if insecure :
            # option equivalent a friser de --insecure
            c.setopt(pycurl.SSL_VERIFYPEER, 0)
            c.setopt(pycurl.SSL_VERIFYHOST, 0)
        c.perform()
        c.close()

def recuperefile(datasend, objectxmpp, ippackage, portpackage):
    if not os.path.isdir(datasend['data']['pathpackageonmachine']):
        os.makedirs(datasend['data']['pathpackageonmachine'], mode=0777)
    uuidpackage = datasend['data']['path'].split('/')[-1]
    curlurlbase = "https://%s:%s/mirror1_files/%s/"%(ippackage, portpackage, uuidpackage )
    for filepackage in datasend['data']['packagefile']:
        if datasend['data']['methodetransfert'] == "pullcurl":
            dest = os.path.join(datasend['data']['pathpackageonmachine'], filepackage)
            urlfile = curlurlbase + filepackage
            try:
                objectxmpp.xmpplog('download from %s file : %s'%(curlgetdownloadfile, filepackage ),
                                    type = 'deploy',
                                    sessionname = datasend['sessionid'],
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Download | Transfert",
                                    date = None ,
                                    fromuser = "MASTER",
                                    touser = "")
                curlgetdownloadfile( dest, urlfile)
            except Exception:
                objectxmpp.xmpplog('<span style="font-weight: bold;color : red;">STOP DEPLOY ON ERROR : download curl [%s]</span>'%curlurlbase,
                                    type = 'deploy',
                                    sessionname = datasend['sessionid'],
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Download | Transfert",
                                    date = None ,
                                    fromuser = "MASTER",
                                    touser = "")
                objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = datasend['sessionid'],
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | Error | End",
                                    date = None ,
                                    fromuser = "MASTER",
                                    touser = "")
                return False
    return True



def action( objectxmpp, action, sessionid, data, message, dataerreur):

    if objectxmpp.config.agenttype in ['machine']:
        logging.getLogger().debug("###################################################")
        logging.getLogger().debug("#################AGENT MACHINE#####################")
        logging.getLogger().debug("###################################################")
        logging.getLogger().debug("call %s from %s"%(plugin,message['from']))
        logging.getLogger().debug("###################################################")

        logging.getLogger().debug("data plugin %s"%(json.dumps(data, indent = 4)))

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
                                    module = "Deployment | Error | Dependencies | Transfert",
                                    date = None ,
                                    fromuser = "MASTER",
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
                                    module = "Deployment | Dependencies | Transfert",
                                    date = None ,
                                    fromuser = "MASTER",
                                    touser = "")
            objectxmpp.xmpplog( 'DEPLOYMENT TERMINATE',
                                type = 'deploy',
                                sessionname = sessionid,
                                priority = -1,
                                action = "",
                                who = objectxmpp.boundjid.bare,
                                how = "",
                                why = "",
                                module = "Deployment | End",
                                date = None ,
                                fromuser = "MASTER",
                                touser = "")
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
                    print "Quit session %s on error "%sessionid
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
                                    fromuser = "MASTER",
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
                                    module = "Deployment | Dependencies | Transfert",
                                    date = None ,
                                    fromuser = "MASTER",
                                    touser = "")
                    objectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment | End",
                                    date = None ,
                                    fromuser = "MASTER",
                                    touser = "")
                    objectxmpp.session.clearnoevent(sessionid)
                    cleanbacktodeploy(objectxmpp)
                    return

            #signal deploy terminate si session n'ai pas dans back_to_deploy
            if sessionid not in objectxmpp.back_to_deploy:
                # Deployment to finish here.
                print "termine la session %s"%sessionid
                oobjectxmpp.xmpplog('DEPLOYMENT TERMINATE',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment",
                                    date = None ,
                                    fromuser = "MASTER",
                                    touser = "")
                objectxmpp.session.clearnoevent(sessionid)
                cleanbacktodeploy(objectxmpp)
                return

            if sessionid in objectxmpp.back_to_deploy and 'Dependency' in objectxmpp.back_to_deploy[sessionid]:
                if len(objectxmpp.back_to_deploy[sessionid]['Dependency']) > 0:
                    loaddependency = objectxmpp.back_to_deploy[sessionid]['Dependency'].pop()
                    data = copy.deepcopy(objectxmpp.back_to_deploy[sessionid]['packagelist'][loaddependency])
                    objectxmpp.xmpplog('! : dependency [%s] '%(data['name']),
                                       type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment",
                                    date = None ,
                                    fromuser = "MASTER",
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

            if not sessionid in objectxmpp.back_to_deploy:
                objectxmpp.back_to_deploy[sessionid] = {}
                objectxmpp.back_to_deploy[sessionid]['Dependency'] = []
                objectxmpp.back_to_deploy[sessionid]['packagelist'] = {}

            data['deploy'] = data['path'].split("/")[-1]

            data['descriptor']['info']['Dependency'].insert(0,data['deploy'] )
            objectxmpp.back_to_deploy[sessionid]['Dependency'] = objectxmpp.back_to_deploy[sessionid]['Dependency'] + data['descriptor']['info']['Dependency']
            del data['descriptor']['info']['Dependency']
            logging.getLogger().debug("Dependency deployement %s"%(objectxmpp.back_to_deploy[sessionid]['Dependency']))
            #global information to keep for this session
            if not 'ipmachine' in objectxmpp.back_to_deploy[sessionid]:
                #on les sauve
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

        if sessionid in objectxmpp.back_to_deploy and not 'start' in objectxmpp.back_to_deploy[sessionid]:
            # Necessary datas are added.
            # If we do not have these data global has all the dislocation we add them.
            if not 'ipmachine' in data:
                logging.getLogger().debug("addition global informations for deploy mode push dependency")
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
                    objectxmpp.back_to_deploy[sessionid]['count']+=1
                    if objectxmpp.back_to_deploy[sessionid]['count'] > 25:
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
                objectxmpp.back_to_deploy[sessionid]['Dependency']
                logging.getLogger().debug("Start Multi-dependency deployment.")
                logging.getLogger().debug("Dependency list %s"%(objectxmpp.back_to_deploy[sessionid]['Dependency']))
                objectxmpp.xmpplog('! : Start Multi-dependency deployment.\n (dependence list %s)'%(objectxmpp.back_to_deploy[sessionid]['Dependency']),
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment",
                                    date = None ,
                                    fromuser = "MASTER",
                                    touser = "")

                firstinstall =  objectxmpp.back_to_deploy[sessionid]['Dependency'].pop()

                objectxmpp.back_to_deploy[sessionid]['start'] = True
                data = copy.deepcopy(objectxmpp.back_to_deploy[sessionid]['packagelist'][firstinstall])
                objectxmpp.xmpplog('! : first dependency [%s] '%(data['name']),
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = -1,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment",
                                    date = None ,
                                    fromuser = "MASTER",
                                    touser = "")
                try:
                    # Removes all the occurrences of this package if it exists because it is installing
                    objectxmpp.back_to_deploy[sessionid]['Dependency'].remove(firstinstall)
                except Exception:
                    pass
                del(objectxmpp.back_to_deploy[sessionid]['packagelist'][firstinstall])
                save_back_to_deploy(objectxmpp.back_to_deploy)
        #########################################################
        if sessionid in objectxmpp.back_to_deploy:
            # Necessary datas are added.
            # If one has not in data this information is added.
            if not 'ipmachine' in data:
                logging.getLogger().debug("addition global informations for deploy")
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
                                    fromuser = "MASTER",
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
                if not recuperefile(datasend, objectxmpp,  data['ippackageserver'], data['portpackageserver']):
                    logging.getLogger().debug("Error curl")
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
                    return
            datasend['data']['stepcurrent'] = 0 #step initial
            if not objectxmpp.session.isexist(sessionid):
                logging.getLogger().debug("creation session %s"%sessionid)
                objectxmpp.session.createsessiondatainfo(sessionid,  datasession = datasend['data'], timevalid = 10)
                logging.getLogger().debug("update object backtodeploy")
            logging.getLogger().debug("start call gracet")
            grafcet(objectxmpp, datasend)
            logging.getLogger().debug("outing graphcet phase1")
        else:
            objectxmpp.session.sessionsetdata(sessionid, datasend) #save data in session
            grafcet(objectxmpp, datasend)#grapcet va utiliser la session pour travailler.
            logging.getLogger().debug("outing graphcet phase1")
    else:
        logging.getLogger().debug("###################################################")
        logging.getLogger().debug("##############AGENT RELAY SERVER###################")
        logging.getLogger().debug("###################################################")
        if 'transfert' in data \
            and data['transfert'] == True\
                and 'methodetransfert' in data\
                    and data['methodetransfert'] == "pullcurl":
                        #mode pull AM to ARS
                        ### send direct a machine le message de deploy.
            transfertdeploy = {
                                'action': action,
                                'sessionid': sessionid,
                                'data' : data,
                                'ret' : 0,
                                'base64' : False }
            objectxmpp.send_message(mto = objectxmpp.data['jidmachine'],
                                    mbody = json.dumps(transfertdeploy),
                                    mtype = 'chat')
        else:
            # mode push ARS to AM
            # UPLOAD FILE PACKAGE to MACHINE, all dependency
            # We are in the case where it is necessary to install all the packages for the deployment, dependency included
            if not objectxmpp.session.isexist(sessionid):
                logging.getLogger().debug("creation session %s"%sessionid)
                objectxmpp.session.createsessiondatainfo(sessionid,  datasession = data, timevalid = 950)
                ## In push method you must know or install the packages on machine agent
                ## In push mode, the packets are sent to a location depending on reception
                ## one must make a request to AM to know or sent the files.
                ## request message pacquage location
                ## create a message with the deploy sessionid.
                ## action will be a call to a plugin info request here the folder_packages
                askinfo( data['jidmachine'],
                        sessionid,
                        objectxmpp,
                        informationasking = ['folders_packages'],
                        replyaction = action)

                #on installe la clef si elle est pas installee sur machine pour le deploiment
                ####if not 'keyinstall' in data_in_session or data_in_session['keyinstall'] == False:
                ##install keypublic on machine
                #keypublic = get_keypub_ssh()
                #installkeypub = {
                                #'action': "setkeypubliconauthorizedkeys",
                                #'sessionid': sessionid,
                                #'data' : {'keypub' : keypublic,
                                #'install' : True,
                                #'actionasker' : action },
                                #'ret' : 0,
                                #'base64' : False }
                #print "######################## SEND keyinstall##########################"
                #objectxmpp.send_message(mto =  data['jidmachine'],
                                        #mbody = json.dumps(installkeypub),
                                        #mtype = 'chat')
            else:
                # The session exists
                print "LA SESSION EXISTE"
                objsession = objectxmpp.session.sessionfromsessiondata(sessionid)
                data_in_session = objsession.getdatasession()
                print "LA SESSION EXISTE"
                if 'step' not in data:
                    print "STEP NOT"
                    if 'keyinstall' in data and data['keyinstall'] == True:
                        # We manage the message condition installation key
                        print "keyinstall in true"
                        data_in_session['keyinstall'] = True
                        objsession.setdatasession(data_in_session)


                    if 'actiontype' in data and 'folders_packages' in data and data['actiontype'] == 'requestinfo' :
                        print "folders_packages"
                        data_in_session['folders_packages'] = data['folders_packages']
                        objsession.setdatasession(data_in_session)


                    # We verify that we have all the information for the deployment
                    if 'folders_packages' in data_in_session and data_in_session['folders_packages'] == "":
                        # termine deploy on error
                        # We do not know folders_packages
                        logging.getLogger().debug("SORRY DEPLOY TERMINATE FOLDERS_PACKAGE MISSING")
                        objectxmpp.xmpplog('<span style="color: red;";>[xxx]: Terminate deploy ERROR folders_packages %s missing</span>',
                                    type = 'deploy',
                                    sessionname = sessionid,
                                    priority = 0,
                                    action = "",
                                    who = objectxmpp.boundjid.bare,
                                    how = "",
                                    why = "",
                                    module = "Deployment|Error",
                                    date = None ,
                                    fromuser = "MASTER",
                                    touser = "")
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
                    logging.getLogger().debug("#################LIST PACKAGE DEPLOY SESSION #######################")
                    logging.getLogger().debug(list_of_deployment_packages)
                    # saves the list of packages to be transferred in the session.
                    data_in_session['transferfiles'] = [x for x in list(list_of_deployment_packages) if x != ""]
                    objsession.setdatasession(data_in_session)
                    ### this plugin will call itself itself is transfer each time a package from the list of packages to transfer.
                    ### to make this call we prepare a message with the current session.
                    ### on the message ['step'] of the message or resume processing.
                    ### here data ['step'] = "transferfiles"
                    logging.getLogger().debug("APPEL POUR PHASE DE TRANSFERTS" )
                    msg_self_call = create_message_self_for_transfertfile(sessionid)
                    objectxmpp.send_message(mto = objectxmpp.boundjid.bare,
                                            mbody = json.dumps(msg_self_call),
                                            mtype = 'chat')
                else:
                    ########## session transfer file ##########
                    #analysis of the resume variable (step)
                    if data['step'] == "transferfiles":
                        logging.getLogger().debug("SESSION TRANSFERT PACKAGES" )
                        logging.getLogger().debug("DATA est %s"%json.dumps(data, indent = 4) )

                        if 'transferfiles' in data_in_session and len ( data_in_session['transferfiles']) != 0:
                            uuidpackages = data_in_session['transferfiles'].pop(0)
                            pathin = managepackage.getpathpackage(uuidpackages)
                            #This variable will be in the future used for the transferrt version of rsync files
                            #pathout = "%s/%s"%(data_in_session['folders_packages'],pathin.split('/')[-1])
                            # Update the session for the next call.
                            # The transferred package is excluded from the list of future packages to install
                            objsession.setdatasession(data_in_session)
                            logging.getLogger().debug("SEND COMMANDE")
                            logging.getLogger().debug("TRANSFERT PACKAGE from %s"%pathin)
                            #The rsync command will have this form
                            #cmd = "rsync --delete -e \"ssh -o IdentityFile=/root/.ssh/id_rsa -o StrictHostKeyChecking=no -o Batchmode=yes -o PasswordAuthentication=no -o ServerAliveInterval=10 -o CheckHostIP=no -o ConnectTimeout=10\"   -av %s/ %s@%s:\"%s/\""%(pathin, "pulse", data_in_session['ipmachine'], pathout)
                            cmd = "scp -r -o IdentityFile=/root/.ssh/id_rsa "\
                                    "-o StrictHostKeyChecking=no "\
                                    "-o UserKnownHostsFile=/dev/null "\
                                    "-o Batchmode=yes "\
                                    "-o PasswordAuthentication=no "\
                                    "-o ServerAliveInterval=10 "\
                                    "-o CheckHostIP=no "\
                                    "-o ConnectTimeout=10 "\
                                        "%s %s@%s:\"\\\"%s\\\"\""%( pathin,
                                                        "pulse",
                                                        data_in_session['ipmachine'],
                                                        data_in_session['folders_packages'])

                            logging.getLogger().debug("tranfert cmd :\n %s"%cmd)
                            obcmd = simplecommandstr(cmd)
                            objectxmpp.xmpplog("push transfert package :%s to %s"%(uuidpackages,data_in_session['jidmachine'] ),
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = objectxmpp.boundjid.bare,
                                                how = "",
                                                why = "",
                                                module = "Deployment|Error",
                                                date = None ,
                                                fromuser = "MASTER",
                                                touser = "")
                            if obcmd['code'] != 0:
                                objectxmpp.xmpplog('<span style="color: red;";>[xxx]: Terminate deploy ERROR transfert %s </span>'%obcmd['result'],
                                                type = 'deploy',
                                                sessionname = sessionid,
                                                priority = -1,
                                                action = "",
                                                who = objectxmpp.boundjid.bare,
                                                how = "",
                                                why = "",
                                                module = "Deployment | Error",
                                                date = None ,
                                                fromuser = "MASTER",
                                                touser = "")
                            logging.getLogger().debug("CALL FOR NEXT PACKAGE")

                            objectxmpp.send_message(mto = objectxmpp.boundjid.bare,
                                                mbody = json.dumps(create_message_self_for_transfertfile(sessionid)),
                                                mtype = 'chat')
                        else:
                            ##undinstall keypublic on machine after transfert package
                            #keypublic = get_keypub_ssh()
                            #undinstallkeypub = {
                                                #'action': "setkeypubliconauthorizedkeys",
                                                #'sessionid': sessionid,
                                                #'data' : {'keypub' : keypublic, 'install' : False},
                                                #'ret' : 0,
                                                #'base64' : False }
                            #objectxmpp.send_message(mto = data_in_session['jidmachine'],
                                                #mbody = json.dumps(undinstallkeypub),
                                                #mtype = 'chat')
                            # Creation of the message from depoy to machine
                            logging.getLogger().debug("APPEL PLUGIN FOR DEPLOY ON MACHINE")
                            transfertdeploy = {
                                                'action': action,
                                                'sessionid': sessionid,
                                                'data' : data_in_session,
                                                'ret' : 0,
                                                'base64' : False }
                            logging.getLogger().debug(json.dumps(transfertdeploy, indent = 4))
                            objectxmpp.send_message(mto = data_in_session['jidmachine'],
                                    mbody = json.dumps(transfertdeploy),
                                    mtype = 'chat')


