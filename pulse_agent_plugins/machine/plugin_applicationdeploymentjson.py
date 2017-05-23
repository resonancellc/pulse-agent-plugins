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
from lib.managepackage import managepackage

from lib.grafcetdeploy import grafcet
import traceback
import pprint
import logging
import pycurl
import platform
from lib.utils import shellcommandtimeout, save_back_to_deploy, load_back_to_deploy, listback_to_deploy, cleanbacktodeploy
import copy

logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25
plugin = { "VERSION" : "1.3", "NAME" : "applicationdeploymentjson", "TYPE" : "machine" }


"""
Plugins for deploiment application 
"""

#TQ type message query
#TR type message Reponse
#TE type message Error
#TED type message END deploy
#TEVENT remote event

def cleandescriptor(datasend):

    if sys.platform.startswith('linux'):
        typeos="Linux"
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
        typeos="Win"
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
    datasend['typeos']=sys.platform
    return True

def keyssh(name="id_rsa.pub"):
    source = open(os.path.join('/','root','.ssh',name), "r")
    dede = source.read().strip(" \n\t")
    source.close()
    return dede

def installkeyssh(keystr):
    if sys.platform.startswith('linux'):
        authorized_keys=os.path.join('/','root','.ssh','authorized_keys')
    elif sys.platform.startswith('win'):
        authorized_keys=os.path.join('C',os.environ["ProgramFiles"],'Pulse','.ssh','authorized_keys')
    elif sys.platform.startswith('darwin'):
        authorized_keys=os.path.join('var','root','.ssh','authorized_keys')
    else:
        pass
    #print authorized_keys
    #recherche si clef in authorized_keys
    addkey = True
    source = open(authorized_keys, "r")
    for ligne in source:
        if keystr in ligne:
            addkey = False
            break
    source.close()
    if addkey:
        source = open(authorized_keys, "a")
        source.write('\n')
        source.write(keystr)
        source.close()

def updatedescriptor(result,descriptor,Devent,Daction):
    if sys.platform.startswith('linux'):
        dataupdate = descriptor['linux']['sequence']
    elif sys.platform.startswith('win'):
        dataupdate = descriptor['win']['sequence']
    elif sys.platform.startswith('darwin'):
        dataupdate = descriptor['Macos']['sequence']
    else:
        return
    for t in dataupdate:
        if t['event'] == Devent and t['action'] == Daction:
            t['codeerror'] = result['codeerror']
            for z in result:
                t[z] = result[z]

def transfert_package(destinataire, datacontinue, objectxmpp):
    logging.getLogger().debug("%s"% json.dumps(datacontinue, indent=4, sort_keys=True))
    if datacontinue['data']['methodetransfert'] == 'rsync':
        if 'Pulse' in datacontinue['data']['pathpackageonmachine'] and 'tmp' in datacontinue['data']['pathpackageonmachine']:

            datacontinue['data']['pathpackageonmachine'] = datacontinue['data']['pathpackageonmachine'].replace("\\","/")
            tab=datacontinue['data']['pathpackageonmachine'].split('/')[3:]
            datacontinue['data']['pathpackageonmachine'] = '/'.join(tab)
            cmd = "rsync --delete -e \"ssh -o IdentityFile=/root/.ssh/id_rsa -o StrictHostKeyChecking=no -o Batchmode=yes -o PasswordAuthentication=no -o ServerAliveInterval=10 -o CheckHostIP=no -o ConnectTimeout=10\" -av %s/ pulse@%s:\"%s/\""%(datacontinue['data']['path'],
                                        datacontinue['data']['ipmachine'],
                                        datacontinue['data']['pathpackageonmachine'])
        else:
            cmd = "rsync --delete -e \"ssh -o IdentityFile=/root/.ssh/id_rsa -o StrictHostKeyChecking=no -o Batchmode=yes -o PasswordAuthentication=no -o ServerAliveInterval=10 -o CheckHostIP=no -o ConnectTimeout=10\"   -av %s/ %s:\"%s/\""%(datacontinue['data']['path'],
                                        datacontinue['data']['ipmachine'],
                                        datacontinue['data']['pathpackageonmachine'])
        logging.getLogger().debug("cmd %s"% cmd)
        logging.getLogger().debug("datacontinue %s"% json.dumps(datacontinue, indent=4, sort_keys=True))
        logging.getLogger().debug("destinataire %s"% destinataire)
        objectxmpp.process_on_end_send_message_xmpp.add_processcommand( cmd ,datacontinue, destinataire, destinataire, 50)
    else:
        pass

def checkosindescriptor(descriptor):
    if sys.platform.startswith('linux'):
        osinstall = 'linux'
    elif sys.platform.startswith('win'):
        osinstall = 'win'
    elif sys.platform.startswith('darwin'):
        osinstall = 'Macos'
    if osinstall in descriptor and 'sequence' in descriptor[osinstall]:
        return True
    else:
        return False

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
        if datasend['data']['methodetransfert'] == "curl":
            dest = os.path.join(datasend['data']['pathpackageonmachine'], filepackage)
            urlfile= curlurlbase + filepackage
            try:
                objectxmpp.logtopulse('download from %s file : %s'%(curlgetdownloadfile, filepackage ) ,
                                       type='deploy',
                                       sessionname = datasend['sessionid'] ,
                                       priority = -1,
                                       who = objectxmpp.boundjid.bare)
                curlgetdownloadfile( dest, urlfile)
            except Exception:
                objectxmpp.logtopulse('<span style="font-weight: bold;color : red;">STOP DEPLOY ON ERROR : download curl [%s]</span>'%curlurlbase, 
                                  type='deploy',
                                  sessionname = datasend['sessionid'],
                                  priority = -1,
                                  who=objectxmpp.boundjid.bare)
                objectxmpp.logtopulse('DEPLOYMENT TERMINATE', 
                            type='deploy',
                            sessionname = datasend['sessionid'] ,
                            priority = -1,
                            who=objectxmpp.boundjid.bare)
                return False
    return True

def action( objectxmpp, action, sessionid, data, message, dataerreur):
    logging.log(DEBUGPULSEPLUGIN,"plugin %s on %s %s from %s"% (plugin,objectxmpp.config.agenttype, message['to'], message['from']))
    #logging.getLogger().debug("data plugin %s"%(json.dumps(data, indent=4)))
    #print json.dumps(data, indent=4)
    ##objectxmpp.session.afficheid()
    ##listback_to_deploy(objectxmpp)

    #Si une dépendance n'existe pas, relay serveur le signale.
    if 'descriptor' in data and data['descriptor'] == "error package missing":
        #package data['deploy'] is missing
        #il faut termined le deploy
        objectxmpp.logtopulse('<span style="font-weight: bold;color : red;">STOP DEPLOY ON ERROR : DEPENDENCY MISSING [%s]</span>'%data['deploy'], 
                                  type='deploy',
                                  sessionname = sessionid ,
                                  priority = -1,
                                  who=objectxmpp.boundjid.bare)
        if sessionid in objectxmpp.back_to_deploy:
            objectxmpp.logtopulse('<span style="font-weight: bold;color : red;">List of abandoned dependencies %s</span>'%objectxmpp.back_to_deploy[sessionid]['Dependency'],
                            type='deploy',
                            sessionname = sessionid ,
                            priority = -1,
                            who=objectxmpp.boundjid.bare)
        objectxmpp.logtopulse('DEPLOYMENT TERMINATE', 
                            type='deploy',
                            sessionname = sessionid ,
                            priority = -1,
                            who=objectxmpp.boundjid.bare)
        #clean session
        objectxmpp.session.clearnoevent(sessionid)
        #clean if not session
        cleanbacktodeploy(objectxmpp)
        return

    if len(data) == 0:
        if 'msgstate' in message['body'] and 'msg' in message['body']['msgstate']  and message['body']['msgstate']['msg'].startswith("end error"):
            if message['body']['msgstate']['quitonerror']:
                print "Quit session %s on error "%sessionid
                objectxmpp.logtopulse('<span style="font-weight: bold;color : red;">STOP DEPLOY ON ERROR</span>', 
                                  type='deploy',
                                  sessionname = sessionid ,
                                  priority = -1,
                                  who=objectxmpp.boundjid.bare)
                if sessionid in objectxmpp.back_to_deploy:
                    objectxmpp.logtopulse('<span style="font-weight: bold;color : red;">List of abandoned dependencies %s</span>'%objectxmpp.back_to_deploy[sessionid]['Dependency'],
                                    type='deploy',
                                    sessionname = sessionid ,
                                    priority = -1,
                                    who=objectxmpp.boundjid.bare)
                objectxmpp.logtopulse('DEPLOYMENT TERMINATE', 
                                  type='deploy',
                                  sessionname = sessionid ,
                                  priority = -1,
                                  who=objectxmpp.boundjid.bare)
                objectxmpp.session.clearnoevent(sessionid)
                cleanbacktodeploy(objectxmpp)
                return

        if sessionid not in objectxmpp.back_to_deploy:
            # deployement terminer ici.
            print "termine la session %s"%sessionid
            objectxmpp.logtopulse('DEPLOYMENT TERMINATE', 
                                  type='deploy',
                                  sessionname = sessionid ,
                                  priority = -1,
                                  who=objectxmpp.boundjid.bare)
            objectxmpp.session.clearnoevent(sessionid)
            cleanbacktodeploy(objectxmpp)
            return

        if sessionid in objectxmpp.back_to_deploy and 'Dependency' in objectxmpp.back_to_deploy[sessionid]:
            if len(objectxmpp.back_to_deploy[sessionid]['Dependency']) > 0:
                loaddependency = objectxmpp.back_to_deploy[sessionid]['Dependency'].pop()
                data = copy.deepcopy(objectxmpp.back_to_deploy[sessionid]['packagelist'][loaddependency])
                objectxmpp.logtopulse('! : dependency [%s] '%(data['name']),
                                       type='deploy',
                                       sessionname = sessionid ,
                                       priority = -1,
                                       who=objectxmpp.boundjid.bare)
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

    if 'Dependency' in data['descriptor']['info'] and  len (data['descriptor']['info'] ['Dependency']) != 0:
        #on deploy pas imediatement
        #on prepare le deployement pour la suite

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
                objectxmpp.send_message(   mto=data['jidrelay'],
                                            mbody=json.dumps(datasend),
                                            mtype='chat')
                if sessionid in objectxmpp.back_to_deploy:
                    save_back_to_deploy(objectxmpp.back_to_deploy)
                return
        else:
            # All dependencies are taken into account. 
            # You must deploy the descriptors of the dependency list starting with the end (pop)
            objectxmpp.back_to_deploy[sessionid]['Dependency']
            logging.getLogger().debug("Start Multi-dependency deployment.")
            logging.getLogger().debug("Dependency list %s"%(objectxmpp.back_to_deploy[sessionid]['Dependency']))
            objectxmpp.logtopulse('! : Start Multi-dependency deployment.\n (dependence list %s)'%(objectxmpp.back_to_deploy[sessionid]['Dependency']),
                                       type='deploy',
                                       sessionname = sessionid ,
                                       priority = -1,
                                       who=objectxmpp.boundjid.bare)

            firstinstall =  objectxmpp.back_to_deploy[sessionid]['Dependency'].pop()

            objectxmpp.back_to_deploy[sessionid]['start'] = True
            data = copy.deepcopy(objectxmpp.back_to_deploy[sessionid]['packagelist'][firstinstall])
            objectxmpp.logtopulse('! : first dependency [%s] '%(data['name']),
                                       type='deploy',
                                       sessionname = sessionid ,
                                       priority = -1,
                                       who=objectxmpp.boundjid.bare)
            try:
                # Removes all the occurrences of this package if it exists because it is installing
                objectxmpp.back_to_deploy[sessionid]['Dependency'].remove(firstinstall)
            except Exception:
                pass
            del(objectxmpp.back_to_deploy[sessionid]['packagelist'][firstinstall])
            save_back_to_deploy(objectxmpp.back_to_deploy)
    #########################################################
    if sessionid in objectxmpp.back_to_deploy:
        # on ajoute les datas nécaisaire.
        # si on a pas dans data ces information on les rajoute.
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
            objectxmpp.logtopulse('<span style="color: red;";>[xxx]: Terminate deploy ERROR descriptor OS %s missing</span>'%sys.platform,
                                        type='deploy',
                                        sessionname = sessionid ,
                                        priority =0,
                                        who=objectxmpp.boundjid.bare)
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
                                            mbody=json.dumps(datasend),
                                            mtype='chat')
            objectxmpp.send_message(   mto=data['jidmaster'],
                                            mbody=json.dumps(datasend),
                                            mtype='chat')
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
        if data['methodetransfert'] == "curl" and data['transfert'] :
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
                                                mbody=json.dumps(datasend),
                                                mtype='chat')
                objectxmpp.send_message(   mto=data['jidmaster'],
                                                mbody=json.dumps(datasend),
                                                mtype='chat')
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
