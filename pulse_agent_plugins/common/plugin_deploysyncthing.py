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
# file : /common/deploysyncthing.py

import os
import sys
import logging
import json
import zlib
import base64
from random import randint
import traceback
from lib.utils import file_put_contents, file_get_contents, getRandomName, simplecommand
#from lib.update_remote_agent import Update_Remote_Agent
import time
from lib.managepackage import managepackage, search_list_of_deployment_packages
import shutil
from sleekxmpp import jid

plugin={"VERSION": "1.062", 'VERSIONAGENT' : '2.0.0', "NAME" : "deploysyncthing", "TYPE" : "all"}

logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25

def action( objectxmpp, action, sessionid, data, message, dataerreur):
    logger.debug("###################################################")
    logger.debug("call %s from %s"%(plugin, message['from']))
    logger.debug("sessionid : %s"%sessionid)
    logger.debug("###################################################")
    data['sessionid'] = sessionid
    datastring =  json.dumps(data, indent = 4)
    print datastring
    if objectxmpp.config.agenttype in ['machine']:
        logger.debug("#################AGENT MACHINE#####################")
        if "subaction" in data :
            logger.debug("subaction : %s"%data['subaction'])
            if data['subaction'] == "notify_machine_deploy_syncthing":
                objectxmpp.syncthing.get_db_completion(data['id_deploy'], objectxmpp.syncthing.device_id)
                # savedata fichier sessionid.ars
                namesessionidars = os.path.join(objectxmpp.dirsyncthing,"%s.ars"%sessionid)
                file_put_contents(namesessionidars, datastring)
                logger.debug("creation file %s"%namesessionidars)
                objectxmpp.xmpplog("creation file %s"%namesessionidars,
                                    type='deploy',
                                    sessionname=sessionid,
                                    priority=-1,
                                    action="",
                                    who="",
                                    how="",
                                    why=objectxmpp.boundjid.bare,
                                    module="Deployment | Syncthing",
                                    date=None,
                                    fromuser="",
                                    touser="")
            elif data['subaction'] == "cleandeploy":
                #TODO: this action will be implemented
                # call suppression partage syncthing
                if 'iddeploy' in data:
                    logger.debug("Delete partage %s if exist"%data['iddeploy'])
                    #objectxmpp.syncthing.delete_folder_id_pulsedeploy(data['iddeploy'])
                    #objectxmpp.syncthing.del_folder(data['iddeploy'])
                    objectxmpp.syncthing.delete_folder_pulse_deploy(data['iddeploy'])
        else:
            namesessioniddescriptor = os.path.join(objectxmpp.dirsyncthing,"%s.descriptor"%sessionid)
            file_put_contents(namesessioniddescriptor, json.dumps(data, indent =4))
            logger.debug("creation file %s"%namesessioniddescriptor)
            objectxmpp.xmpplog( "creation file %s"%namesessioniddescriptor,
                                type='deploy',
                                sessionname=sessionid,
                                priority=-1,
                                action="",
                                who="",
                                how="",
                                why=objectxmpp.boundjid.bare,
                                module="Deployment | Syncthing",
                                date=None,
                                fromuser="",
                                touser="")
    else:
        try:
            logger.debug("##############AGENT RELAY SERVER###################")
            """ les devices des autre ARS sont connue, on initialise uniquement le folder."""
            basesyncthing = "/var/lib/syncthing/partagedeploy"
            if not os.path.exists(basesyncthing):
                os.makedirs(basesyncthing)
            if "subaction" in data :
                logger.debug("subaction : %s"%data['subaction'])
                if data['subaction'] == "syncthingdeploycluster":
                    packagedir = managepackage.packagedir()
                    # creation fichier de partages syncthing
                    repertorypartage = os.path.join(basesyncthing,data['repertoiredeploy'] )
                    if not os.path.exists(repertorypartage):
                        os.makedirs(repertorypartage)
                    cmd = "touch %s"%os.path.join(repertorypartage,'.stfolder')
                    logger.debug("cmd : %s"%cmd)
                    obj = simplecommand(cmd)
                    if int(obj['code']) != 0:
                        logger.warning(obj['result'])
                    list_of_deployment_packages =\
                        search_list_of_deployment_packages(data['packagedeploy']).\
                            search()
                    logger.warning("copy to repertorypartage")
                    #on copy les packages dans le repertoire de  partages"
                    for z in list_of_deployment_packages:
                        repsrc = os.path.join(packagedir,str(z) )
                        cmd = "rsync -r %s %s/"%( repsrc , repertorypartage)
                        logger.debug("cmd : %s"%cmd)
                        obj = simplecommand(cmd)
                        if int(obj['code']) != 0:
                            logger.warning(obj['result'])
                        else:
                            objectxmpp.xmpplog( "ARS %s repertory partage %s"%(objectxmpp.boundjid.bare,
                                                repertorypartage),
                                                type='deploy',
                                                sessionname=sessionid,
                                                priority=-1,
                                                action="",
                                                who="",
                                                how="",
                                                why=objectxmpp.boundjid.bare,
                                                module="Deployment | Syncthing",
                                                date=None,
                                                fromuser="",
                                                touser="")
                    cmd ="chown syncthing:syncthing -R %s"%repertorypartage
                    logger.debug("cmd : %s"%cmd)
                    obj = simplecommand(cmd)
                    if int(obj['code']) != 0:
                        logger.warning(obj['result'])
                    # creation fichier .stfolder

                    #addition des devices. add device ARS si non exist.
                    #creation du partage pour cet
                    if data['elected'].split('/')[0] == objectxmpp.boundjid.bare:
                        typefolder="master"
                    else:
                        typefolder="slave"
                    #creation du folder
                    newfolder = objectxmpp.syncthing.\
                        create_template_struct_folder(data['repertoiredeploy'], # or data['packagedeploy']
                                                    repertorypartage,
                                                    id=data['repertoiredeploy'],
                                                    typefolder=typefolder )

                    objectxmpp.syncthing.add_folder_dict_if_not_exist_id(newfolder)
                    #add device cluster ars in new partage folder
                    for keyclustersyncthing in data['listkey']:
                        objectxmpp.syncthing.add_device_in_folder_if_not_exist( data['repertoiredeploy'],
                                                                                keyclustersyncthing,
                                                                                introducedBy = "")

                    for machine in data['machinespartage']:
                        #add device dans folder
                        objectxmpp.syncthing.add_device_in_folder_if_not_exist( data['repertoiredeploy'],
                                                                                machine['devi'],
                                                                                introducedBy = "")
                        #add device
                        namemachine = jid.JID(machine['mach']).resource
                        if namemachine == "dev-mmc":
                            namemachine = "pulse"
                        if namemachine=="":
                            namemachine = machine['mach']

                        objectxmpp.syncthing.add_device_syncthing( machine['devi'],
                                                                   namemachine)

                        #create message for machine
                        datasend = {'action' : "deploysyncthing",
                                    "sessionid" : machine['ses'],
                                    "ret" : 0,
                                    "base64" : False,
                                    "data" : { "subaction" : "notify_machine_deploy_syncthing",
                                               "id_deploy" : data['repertoiredeploy'],
                                               "namedeploy" : data['namedeploy'],
                                               "packagedeploy" : data['packagedeploy'],
                                               "ARS" : machine['rel'],
                                               "mach" : machine['mach'],
                                               "iddeploybase" : data['id'] }}
                        objectxmpp.send_message(mto=machine['mach'],
                                                mbody=json.dumps(datasend),
                                                mtype='chat')
                        logger.debug("addition device %s for machine %s"%(machine['devi'],
                                                                          machine['mach']))
                elif data['subaction'] == "cleandeploy":
                    #TODO: this action will be implemented
                    # call suppression partage syncthing
                    if 'iddeploy' in data:
                        logger.debug("Delete partage %s if exist"%data['iddeploy'])
                        #objectxmpp.syncthing.delete_folder_id_pulsedeploy(data['iddeploy'])
                        objectxmpp.syncthing.delete_folder_pulse_deploy(data['iddeploy'])
                    messgagesend = {
                        "sessionid" : sessionid,
                        "action" : action,
                        "data" : { "subaction" : "cleandeploy",
                                "iddeploy" : data['iddeploy'] }
                    }
                    machineslist = data['jidmachines'].split(",")
                    relayslist   = data['jidrelays'].split(",")
                    nbrelaylist  = len(relayslist)
                    for index_relay_mach in  range(nbrelaylist):
                        if relayslist[index_relay_mach] == objectxmpp.boundjid.full:
                            #send message machine
                            logger.debug("send Delete partage %s on mach %s"%(data['iddeploy'],
                                                                              machineslist[index_relay_mach]))
                            print "send delete floder to machine %s"%machineslist[index_relay_mach]
                            objectxmpp.send_message(mto=machineslist[index_relay_mach],
                                                    mbody=json.dumps(messgagesend),
                                                    mtype='chat')
                elif data['subaction'] == "pausefolder":
                    if 'folder' in data:
                        logger.debug("pausing folder %s for ARS %s"%(data['folder'], objectxmpp.boundjid.full))
                        objectxmpp.syncthing.set_pause_folder(data['folder'], paused = True)
        except:
            logger.error("\n%s"%(traceback.format_exc()))
            raise
