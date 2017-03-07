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
import sys
import os
from lib.managepackage import managepackage
from lib.grafcetdeploy import grafcet
import traceback
import pprint
import logging
import pycurl

from lib.utils import shellcommandtimeout


logger = logging.getLogger()

plugin = {"VERSION" : "1.1", "NAME" : "applicationdeploymentjson", "TYPE" : "all"}


"""
Plugins for deploiment application
"""



#TQ type message query
#TR type message Reponse
#TE type message Error
#TED type message END deploy
#TEVENT remote event



def cleandescriptor(datasend):

    sequence = {}
    if sys.platform.startswith('linux'):
        typeos = "Linux"
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
        typeos = "Win"
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
        typeos = "Macos"
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
            del datasend['descriptor']['Macos']
        except:
            False
    datasend['typeos'] = sys.platform
    return True

def keyssh(name="id_rsa.pub"):
    source = open(os.path.join('/', 'root', '.ssh', name), "r")
    dede = source.read().strip(" \n\t")
    source.close()
    return dede

def installkeyssh(keystr):
    if sys.platform.startswith('linux'):
        authorized_keys = os.path.join('/', 'root', '.ssh', 'authorized_keys')
    elif sys.platform.startswith('win'):
        authorized_keys = os.path.join('C', os.environ["ProgramFiles"], 'Pulse', '.ssh', 'authorized_keys')
    elif sys.platform.startswith('darwin'):
        authorized_keys = os.path.join('var', 'root', '.ssh', 'authorized_keys')
    else:
        pass
    print authorized_keys
    # Search if the key is in authorized_keys
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

def updatedescriptor(result, descriptor, Devent, Daction):
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

            datacontinue['data']['pathpackageonmachine'] = datacontinue['data']['pathpackageonmachine'].replace("\\", "/")
            tab = datacontinue['data']['pathpackageonmachine'].split('/')[3:]
            datacontinue['data']['pathpackageonmachine'] = '/'.join(tab)
            cmd = "rsync --delete -e \"ssh -o IdentityFile=/root/.ssh/id_rsa -o StrictHostKeyChecking=no -o Batchmode=yes -o PasswordAuthentication=no -o ServerAliveInterval=10 -o CheckHostIP=no -o ConnectTimeout=10\" -av %s/ pulse@%s:\"%s/\""%(datacontinue['data']['path'],
                                        datacontinue['data']['ipmachine'],
                                        datacontinue['data']['pathpackageonmachine'])
        else:
            cmd = "rsync --delete -e \"ssh -o IdentityFile=/root/.ssh/id_rsa -o StrictHostKeyChecking=no -o Batchmode=yes -o PasswordAuthentication=no -o ServerAliveInterval=10 -o CheckHostIP=no -o ConnectTimeout=10\"   -av %s/ %s:\"%s/\""%(datacontinue['data']['path'],
                                        datacontinue['data']['ipmachine'],
                                        datacontinue['data']['pathpackageonmachine'])
        print datacontinue['data']['pathpackageonmachine']
        logging.getLogger().debug("cmd %s"% cmd)
        logging.getLogger().debug("datacontinue %s"% json.dumps(datacontinue, indent=4, sort_keys=True))
        logging.getLogger().debug("destinataire %s"% destinataire)
        objectxmpp.process_on_end_send_message_xmpp.add_processcommand(cmd, datacontinue, destinataire, destinataire, 50)
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


def curlgetdownloadfile(destfile, urlfile, insecure=True):
    # As long as the file is opened in binary mode, both Python 2 and Python 3
    # can write response body to it without decoding.
    with open(destfile, 'wb') as f:
        c = pycurl.Curl()
        c.setopt(c.URL, urlfile)
        c.setopt(c.WRITEDATA, f)
        if insecure:
            # option equivalent a friser de --insecure
            c.setopt(pycurl.SSL_VERIFYPEER, 0)
            c.setopt(pycurl.SSL_VERIFYHOST, 0)
        c.perform()
        c.close()

def recuperefile(datasend, objectxmpp):
    if not os.path.isdir(datasend['data']['pathpackageonmachine']):
        os.makedirs(datasend['data']['pathpackageonmachine'], mode=0777)
    uuidpackage = datasend['data']['path'].split('/')[-1]
    curlurlbase = "https://%s:9990/mirror1_files/%s/"%(datasend['data']['iprelay'], uuidpackage)
    #curl -O -k  https://192.168.56.2:9990/mirror1_files/0be145fa-973c-11e4-8dc5-0800275891ef/7z920.exe
    for filepackage in datasend['data']['packagefile']:
        if datasend['data']['methodetransfert'] == "curl":
            src = os.path.join(datasend['data']['path'], filepackage)
            dest = os.path.join(datasend['data']['pathpackageonmachine'], filepackage)
            urlfile = curlurlbase + filepackage
            print "curl file dest %s  url  %s"%(dest, urlfile)
            curlgetdownloadfile(dest, urlfile)
            objectxmpp.logtopulse('download from %s file : %s'%(datasend['data']['jidrelay'], filepackage),
                                       type='deploy',
                                       sessionname=datasend['sessionid'],
                                       priority=-1,
                                       who=objectxmpp.boundjid.bare)


def action(objectxmpp, action, sessionid, data, message, dataerreur):
    logging.getLogger().debug("RECV data message")
    datasend = {
                    'action': action,
                    'sessionid': sessionid,
                    'data' : data,
                    'ret' : 0,
                    'base64' : False
                }

    logging.getLogger().debug("#################MACHINE#####################")
    logging.getLogger().debug("##############deploy %s on %s##############"%(data['name'], data['jidmachine']))
    logging.getLogger().debug("#############################################")
    if not 'stepcurrent' in datasend['data']:
        if not cleandescriptor(data):
            objectxmpp.logtopulse('[xxx]: Terminate deploy ERROR descriptor OS %s missing'%sys.platform,
                                        type='deploy',
                                        sessionname=sessionid,
                                        priority=0,
                                        who=objectxmpp.boundjid.bare)
            datasend = {
                            'action':  "result" + action,
                            'sessionid': sessionid,
                            'data' : data,
                            'ret' : -1,
                            'base64' : False
                        }
            objectxmpp.logtopulse('[xxx]: Terminate deploy ERROR descriptor OS %s '%sys.platform,
                                        type='deploy',
                                        sessionname=sessionid,
                                        priority=0,
                                        who=objectxmpp.boundjid.bare)
            objectxmpp.send_message(mto='log@pulse',
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
        datasend['data']['pathpackageonmachine'] = os.path.join(managepackage.packagedir(), data['path'].split('/')[-1])
        if data['methodetransfert'] == "curl" and data['transfert']:
            recuperefile(datasend, objectxmpp)
        datasend['data']['stepcurrent'] = 0 #step initial
        if not objectxmpp.session.isexist(sessionid):
            objectxmpp.session.createsessiondatainfo(sessionid, datasession=datasend['data'], timevalid=10)
        logging.getLogger().debug("start call gracet")
        grafcet(objectxmpp, datasend)
    else:
        objectxmpp.session.sessionsetdata(sessionid, datasend) #save data in session
        grafcet(objectxmpp, datasend)#grapcet va utiliser la session pour travaillé.



