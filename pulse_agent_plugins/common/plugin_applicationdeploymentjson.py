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
from lib.grafcetdeploy import sequentialevolutionquery
from lib.grafcetdeploy import grafcet
import traceback
import pprint
import logging


from lib.utils import shellcommandtimeout


logger = logging.getLogger()

plugin = { "VERSION" : "1.1", "NAME" : "applicationdeploymentjson", "TYPE" : "all" }


"""
Plugins for deploiment application 
"""


#TQ type message query
#TR type message Reponse
#TE type message Error
#TED type message END deploy
#TEVENT remote event





def cleandescriptor(datasend):
    sequence= {}
    if sys.platform.startswith('linux'):
        typeos="Linux"
        try:
            del datasend['data']['descriptor']['win']['sequence']
        except KeyError:
            pass
        try:
            del datasend['data']['descriptor']['Macos']['sequence']
        except KeyError:
            pass
        try:
            datasend['data']['descriptor']['sequence'] = datasend['data']['descriptor']['linux']['sequence']
            #del datasend['data']['descriptor']['linux']['sequence']
            del datasend['data']['descriptor']['linux']
        except:
            pass
    elif sys.platform.startswith('win'):
        typeos="Win"
        try:
            del datasend['data']['descriptor']['linux']['sequence']
        except KeyError:
            pass
        try:
            del datasend['data']['descriptor']['Macos']['sequence']
        except KeyError:
            pass
        try:
            datasend['data']['descriptor']['sequence'] = datasend['data']['descriptor']['win']['sequence']
            #del datasend['data']['descriptor']['win']['sequence']
            del datasend['data']['descriptor']['win']
        except:
            pass
    elif sys.platform.startswith('darwin'):
        typeos="Macos"
        try:
            del datasend['data']['descriptor']['linux']['sequence']
        except KeyError:
            pass
        try:
            del datasend['data']['descriptor']['win']['sequence']
        except KeyError:
            pass
        try:
            datasend['data']['descriptor']['sequence'] = datasend['data']['descriptor']['Macos']['sequence']
            #del datasend['data']['descriptor']['Macos']['sequence']
            del datasend['data']['descriptor']['Macos']
        except:
            pass
    datasend['data']['typeos']=typeos
    return datasend



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


def transfert_package(destinataire, datacontinue,objectxmpp):
    logging.getLogger().debug("%s"% json.dumps(datacontinue, indent=4, sort_keys=True))
    if datacontinue['data']['methodetransfert'] == 'rsync':
        cmd = "rsync --delete -av %s/ %s:%s/"%(datacontinue['data']['path'],
                                        datacontinue['data']['ipmachine'],
                                        datacontinue['data']['pathpackageonmachine'])
        logging.getLogger().debug("cmd %s"% cmd)
        logging.getLogger().debug("datacontinue %s"% json.dumps(datacontinue, indent=4, sort_keys=True))
        logging.getLogger().debug("destinataire %s"% destinataire)
        objectxmpp.process_on_end_send_message_xmpp.add_processcommand( cmd ,datacontinue, destinataire, destinataire,   50)
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


def action( objectxmpp, action, sessionid, data, message, dataerreur):
    logging.getLogger().debug("RECV data message")
    #if not 'stepcurrent' in data:
        #logging.getLogger().debug("%s"% json.dumps(data, indent=4, sort_keys=True))
    #define message template
    datasend = {
                    'action': action,
                    'sessionid': sessionid,
                    'data' : data,
                    'ret' : 0,
                    'base64' : False
                }

 
    if objectxmpp.config.agenttype == "relayserver":
        logging.getLogger().debug("###############RELAY SERVER##################")
        logging.getLogger().debug("##############deploy %s on %s##############"%(data['name'],data['jidmachine'] ))
        logging.getLogger().debug("#############################################")
        # creation session relay server if not exist
        # demande deploy sur machine
        print "session est", sessionid
        if not objectxmpp.session.isexist(sessionid):
            #test package exist on relayserver
            print "**************session non existe"
            if managepackage.getpathpackagename(data['name']) is None:
                logging.getLogger().info("packages %s missing on relayserver %s"%(data['name'],data['jidrelay']))
                print "deploye error"
                return
            try:
                #embarquement du descriptaur de deployement
                datasend['data']['descriptor'] =  managepackage.getdescriptorpackagename(data['name'])
                #creation session
                objectxmpp.session.createsessiondatainfo(sessionid,  datasession = data, timevalid = 10)
                logging.getLogger().debug("send data to %s\n %s"%(data['jidmachine'] ,json.dumps(datasend, indent=4, sort_keys=True)))
                objectxmpp.send_message(    mto=data['jidmachine'],
                                            mbody=json.dumps(datasend),
                                            mtype='chat')
                print "attend reponse"
            except Exception as e:
                print str(e)
                traceback.print_exc(file=sys.stdout)
        else:
            try:
                print "**************session existe"
                print  data['Devent']
                print data['Dtypequery']
                print "**************session existe"
                if data['Devent'] ==  "packagesmissing" and data['Dtypequery'] == "TR":
                    print  "packagesmissing"
                    # il faut installer package sur machine.
                    logging.getLogger().warn("package missing %s on machine %s"%(data['name'],data['jidmachine']))
                    # transfert pacquage
                    #transfert pacquage transfert le package sur machine et relance deploiement.
                    datasend['data'] = data
                    #supprimem os no used descriptor

                    datasend['data']['Devent'] = "STARDEPLOY"
                    datasend['data']['Dtypequery'] = "TQ"
                    transfert_package(data['jidmachine'],datasend,objectxmpp)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
        print "quit relayserver"
    else:
        logging.getLogger().debug("#################MACHINE#####################")
        logging.getLogger().debug("##############deploy %s on %s##############"%(data['name'],data['jidmachine'] ))
        logging.getLogger().debug("#############################################")
        #test package exist sur machine
        #print "recois message"
        #print json.dumps(data, indent=4, sort_keys=True)
        try:
            if not 'stepcurrent' in datasend['data']:

                if not 'sequence' in datasend['data']['descriptor'] and not checkosindescriptor(datasend['data']['descriptor']):
                    print 'no checkosindescriptor'
                    return 

                datasend = cleandescriptor(datasend)
                datasend['data']['pathpackageonmachine'] = os.path.join( managepackage.packagedir(),data['path'].split('/')[-1])

                if managepackage.getpathpackagename(data['name']) is None:
                    logging.getLogger().warn("packages %s missing on machine %s"%(data['name'], data['jidmachine']))
                    datasend['data']['Devent'] = "packagesmissing"
                    datasend['data']['Dtypequery'] = "TR"
                    #namepackage = data['path'].split('/')[-1]
                    #logging.getLogger().debug("SEND data to %s "%data['jidrelay'])
                    logging.getLogger().debug("send envoi relayserver %s"% json.dumps(datasend, indent=4, sort_keys=True))
                    objectxmpp.send_message(    mto=data['jidrelay'],
                                                    mbody=json.dumps(datasend),
                                                    mtype='chat')
                else:
                    if not 'stepcurrent' in datasend['data']:
                        # data['stepcurrent'] est la tache qui va etre effectué.
                        datasend['data']['stepcurrent'] = 0 #step initial
                        logging.getLogger().debug("presence packages %s on machine %s"%(datasend['data']['name'], datasend['data']['jidmachine']))
                        logging.getLogger().debug("start deploiement")
                        # creation d'une session
                        if not objectxmpp.session.isexist(sessionid):
                            objectxmpp.session.createsessiondatainfo(sessionid,  datasession = datasend['data'], timevalid = 10)
                        #logging.getLogger().info("%s"% json.dumps(datasend, indent=4, sort_keys=True))
                        logging.getLogger().debug("start call gracet")
                        grafcet(objectxmpp, datasend) # initialise graphcetgrapcet
            else:
                print "creation session"
                objectxmpp.session.sessionsetdata(sessionid, datasend) #save data in session
                print "grapcet"
                grafcet(objectxmpp, datasend)#grapcet va utiliser la session pour travaillé.

        except Exception as e:
                traceback.print_exc(file=sys.stdout)
