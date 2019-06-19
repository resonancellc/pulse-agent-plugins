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

plugin={"VERSION": "1.038", 'VERSIONAGENT' : '2.0.0', "NAME" : "deploysyncthing", "TYPE" : "all"}

logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25

def adddevicesyncthing(objectxmpp,
                       keydevicesyncthing, 
                       namerelay, 
                       introducer = False):
    resource = jid.JID(namerelay).resource
    if resource == "dev-mmc":
        resource = "pulse"
    if resource=="":
        resource = namerelay
    if not is_exist_device_in_config(objectxmpp, keydevicesyncthing):
        logger.debug("add device syncthing %s"%keydevicesyncthing)
        dsyncthing_tmp = objectxmpp.syncthing.\
            create_template_struct_device( resource,
                                            str(keydevicesyncthing),
                                            introducer = introducer,
                                            autoAcceptFolders=False)
        logger.debug("add device [%s]syncthing to ars %s\n%s"%(keydevicesyncthing,
                                                                namerelay,
                                                                json.dumps(dsyncthing_tmp,
                                                                        indent = 4)))
        objectxmpp.syncthing.config['devices'].append(dsyncthing_tmp)
        logger.debug("synchro config %s"%objectxmpp.syncthing.is_config_sync())

def is_exist_device_in_config(objectxmpp, keydevicesyncthing):
    for device in objectxmpp.syncthing.devices:
        if device['deviceID'] == keydevicesyncthing:
            return True
    return False

def action( objectxmpp, action, sessionid, data, message, dataerreur):
    logger.debug("###################################################")
    logger.debug("call %s from %s"%(plugin, message['from']))
    logger.debug("###################################################")
    data['sessionid'] = sessionid
    datastring =  json.dumps(data, indent = 4)
    if objectxmpp.config.agenttype in ['machine']:
        logger.debug("#################AGENT MACHINE#####################")
        if "subaction" in data :
            if data['subaction'] == "notify_machine_deploy_syncthing":
                print objectxmpp.syncthing.get_db_completion(data['id_deploy'], objectxmpp.syncthing.device_id)
                # savedata fichier sessionid.ars
                namesessionidars = os.path.join(objectxmpp.dirsyncthing,"%s.ars"%sessionid)
                file_put_contents(namesessionidars, datastring)
                logger.debug("creation file %s"%namesessionidars)
        else:
            namesessioniddescriptor = os.path.join(objectxmpp.dirsyncthing,"%s.descriptor"%sessionid)
            file_put_contents(namesessioniddescriptor, json.dumps(data, indent =4))
            logger.debug("creation file %s"%namesessioniddescriptor)
    else:
        logger.debug("##############AGENT RELAY SERVER###################")
        """ les devices des autre ARS sont connue, on initialise uniquement le folder."""
        basesyncthing = "/var/lib/syncthing/partagedeploy"
        if not os.path.exists(basesyncthing):
            os.makedirs(basesyncthing)
 
        if "subaction" in data :#
            if data['subaction'] == "syncthingdeploycluster":
                packagedir = managepackage.packagedir()
                # creation fichier de partages syncthing
                repertorypartage = os.path.join(basesyncthing,data['repertoiredeploy'] )
                if not os.path.exists(repertorypartage):
                    os.makedirs(repertorypartage)
                cmd = "touch %s"%os.path.join(repertorypartage,'.stfolder')
                logger.debug("cmd : %s"%cmd)
                obj = simplecommand(cmd)
                if int(obj['code']) == 0:
                    print "creation  .stfolder"
                else:
                    print obj['result']

                list_of_deployment_packages =\
                    search_list_of_deployment_packages(data['packagedeploy']).\
                        search()
                print list_of_deployment_packages
                print repertorypartage
                print packagedir
                print basesyncthing
                print "copy to repertorypartage"
                #on copy les packages dans le repertoire de  partages"
                for z in list_of_deployment_packages:
                    repsrc = os.path.join(packagedir,str(z) )
                    cmd = "rsync -r %s %s/"%( repsrc , repertorypartage)
                    logger.debug("cmd : %s"%cmd)
                    obj = simplecommand(cmd)
                    if int(obj['code']) == 0:
                        print "copy success"
                    else:
                        print obj['result']
                cmd ="chown syncthing:syncthing -R %s"%repertorypartage
                logger.debug("cmd : %s"%cmd)
                obj = simplecommand(cmd)
                if int(obj['code']) == 0:
                    print "repertoire syncthing"
                else:
                    print obj['result']
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
                #add device cluster ars in new partage folder
                for keyclustersyncthing in data['listkey']:
                    objectxmpp.syncthing.add_device_in_folder(newfolder, keyclustersyncthing)

                for machine in data['machinespartage']:
                    #add device dans folder
                    objectxmpp.syncthing.add_device_in_folder(newfolder, machine['devi'])
                    #add device
                    adddevicesyncthing(objectxmpp, machine['devi'],  machine['mach'])
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
                                           "mach" : machine['mach']}}
                    objectxmpp.send_message(mto=machine['mach'],
                                            mbody=json.dumps(datasend),
                                            mtype='chat')

                #reinitialisation syncthing conf
                if objectxmpp.syncthing.add_folder_dict_if_not_exist_id(newfolder):
                    objectxmpp.syncthing.validate_chang_config()

                print "addition partage"
                print json.dumps(objectxmpp.syncthing.config, indent = 4)
                #print json.dumps(newfolder, indent = 4)
