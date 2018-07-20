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
# file : /common/plugin_updateagent.py
import os
import sys
import logging
import json
import zlib
import base64
from random import randint
from time import sleep
import traceback
from lib.utils import file_put_contents, file_get_contents
from lib.update_remote_agent import Update_Remote_Agent
plugin={"VERSION": "1.001", "NAME" : "updateagent", "TYPE" : "all", "waittingmax" : 35, "waittingmin" : 5}

logger = logging.getLogger()
DEBUGPULSEPLUGIN = 25

def action( objectxmpp, action, sessionid, data, message, dataerreur):
    logger.debug("###################################################")
    logger.debug("call %s from %s"%(plugin, message['from']))
    logger.debug("###################################################")
    if "subaction" in data :
        if data['subaction'] == "descriptor":
            difference = { }
            sublibdifference = { }
            file_put_contents(os.path.join(objectxmpp.pathagent, "BOOL_UPDATE_AGENT"),"use file boolean update. enable verify update.")
            if 'version' in data['descriptoragent']:
                #copy version agent master to image
                file_put_contents(os.path.join(objectxmpp.img_agent, "agentversion"),data['descriptoragent']['version'])
                file_put_contents(os.path.join(objectxmpp.pathagent, "agentversion"),data['descriptoragent']['version'])
            #genere
            descriptorimage = Update_Remote_Agent(objectxmpp.img_agent)
            objectxmpp.descriptor_master = data['descriptoragent']

            descriptormachine = descriptorimage.get_md5_descriptor_agent()
            difference['program_agent']= search_diff_agentversion(objectxmpp,data['descriptoragent']['program_agent'], descriptormachine['program_agent'] )
            difference['lib_agent']= search_diff_agentversion(objectxmpp,data['descriptoragent']['lib_agent'], descriptormachine['lib_agent'] )
            difference['script_agent']= search_diff_agentversion(objectxmpp,data['descriptoragent']['script_agent'], descriptormachine['script_agent'] )
            sublibdifference ['program_agent']=search_filesupp_agentversion(objectxmpp,descriptormachine['program_agent'] ,data['descriptoragent']['program_agent'])
            sublibdifference ['lib_agent']=search_filesupp_agentversion(objectxmpp,descriptormachine['lib_agent'] ,data['descriptoragent']['lib_agent'])
            sublibdifference ['script_agent'] = search_filesupp_agentversion(objectxmpp,descriptormachine['script_agent'] ,data['descriptoragent']['script_agent'])
            # attente aleatoire de quelques minutes avant de demander la mise à jour des agents
            try :
                if len(difference['program_agent']) !=0 or len(difference['lib_agent']) !=0 or len(difference['script_agent']) !=0:
                    #sleep(randint(plugin['waittingmin'],plugin['waittingmax']))
                    # demande de mise à jour.
                    #todo send message only files for updating.
                    msgupdate_me = { 'action': "result%s"%action,
                                    'sessionid': sessionid,
                                    'data' :  { "subaction" : "update_me",
                                                "descriptoragent" : difference },
                                    'ret' : 0,
                                    'base64' : False }
                    # renvoi descriptor pour demander la mise a jour
                    objectxmpp.send_message(mto="master@pulse/MASTER",
                                    mbody=json.dumps(msgupdate_me),
                                    mtype='chat')
                    logger.debug("to updating files %s"%json.dumps(difference, indent = 4))
                    logger.debug("to deleting files %s"%json.dumps(sublibdifference, indent = 4))
                    delete_file_image(objectxmpp, sublibdifference)
                    descriptorimage = Update_Remote_Agent(objectxmpp.img_agent)
                    return
                else:
                    return
            except Exception as e:
                logger.error(str(e))
                traceback.print_exc(file=sys.stdout)
        elif data['subaction'] == "install_lib_agent":
            if not ('namescript' in data and data['namescript'] != ""):
                logger.error("update agent install lib name missing")
                return
            else:
                content = zlib.decompress(base64.b64decode(data['content']))
                dump_file_in_img(objectxmpp, data['namescript'], content, "lib_agent")
        elif data['subaction'] == "install_program_agent":
            if not ('namescript' in data and data['namescript'] != ""):
                logger.error("update agent install program name missing")
                return
            else:
                content = zlib.decompress(base64.b64decode(data['content']))
                dump_file_in_img(objectxmpp, data['namescript'], content, "program_agent")
        elif data['subaction'] == "install_script_agent":
            if not ('namescript' in data and data['namescript'] != ""):
                logger.error("updateagent install script name missing")
                return
            else:
                content = zlib.decompress(base64.b64decode(data['content']))
                dump_file_in_img(objectxmpp, data['namescript'], content, "script_agent")

def reinstall_agent_with_image_agent_version_master(objectxmpp):
    newdescriptorimage = Update_Remote_Agent(objectxmpp.img_agent)
    if sys.platform.startswith('win'):
        for fichier in newdescriptorimage.get_md5_descriptor_agent()['program_agent']:
            os.system('copy  %s %s'%(os.path.join(objectxmpp.img_agent, fichier),
                                     os.path.join(objectxmpp.pathagent, fichier)))
            logger.debug('install program agent  %s to %s'%(os.path.join(objectxmpp.img_agent, fichier),
                                                            os.path.join(objectxmpp.pathagent)))
        os.system('copy  %s %s'%(os.path.join(objectxmpp.img_agent, "agentversion"),
                                 os.path.join(objectxmpp.pathagent, "agentversion")))
        for fichier in newdescriptorimage.get_md5_descriptor_agent()['lib_agent']:
            os.system('copy  %s %s'%(os.path.join(objectxmpp.img_agent, "lib", fichier),
                                     os.path.join(objectxmpp.pathagent, "lib", fichier)))
            logger.debug('install lib agent  %s to %s'%(os.path.join(objectxmpp.img_agent, "lib", fichier),
                                                        os.path.join(objectxmpp.pathagent, "lib", fichier)))
        for fichier in newdescriptorimage.get_md5_descriptor_agent()['script_agent']:
            os.system('copy  %s %s'%(os.path.join(objectxmpp.img_agent, "script", fichier),
                                     os.path.join(objectxmpp.pathagent, "script", fichier)))
            logger.debug('install script agent %s to %s'%(os.path.join(objectxmpp.img_agent, "script", fichier),
                                                          os.path.join(objectxmpp.pathagent, "script", fichier)))
        #todo base de reg install version
    elif sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        os.system('cp  %s/*.py %s'%(objectxmpp.img_agent, objectxmpp.pathagent))
        os.system('cp  %s/script/* %s/script/'%(objectxmpp.img_agent, objectxmpp.pathagent))
        os.system('cp  %s/lib/*.py %s/lib/'%(objectxmpp.img_agent, objectxmpp.pathagent))
        os.system('cp  %s/agentversion %s/agentversion'%(objectxmpp.img_agent, objectxmpp.pathagent))
        logger.debug('cp  %s/*.py %s'%(objectxmpp.img_agent, objectxmpp.pathagent))
        logger.debug('cp  %s/script/* %s/script/'%(objectxmpp.img_agent, objectxmpp.pathagent))
        logger.debug('cp  %s/lib/*.py %s/lib/'%(objectxmpp.img_agent, objectxmpp.pathagent))
        logger.debug('cp  %s/agentversion %s/agentversion'%(objectxmpp.img_agent, objectxmpp.pathagent))
    else: 
        logger.error("reinstall agent copy file error os missing")

def dump_file_in_img(objectxmpp, namescript, content, typescript):
    if typescript == "program_agent":
        # install script program
        file_mane = os.path.join(objectxmpp.img_agent, namescript)
        logger.debug("dump file %s to %s"%(namescript, file_mane))
    elif typescript == "script_agent":
        # install script program
        file_mane = os.path.join(objectxmpp.img_agent, "script", namescript)
        logger.debug("dump file %s to %s"%(namescript, file_mane))
    elif typescript == "lib_agent":
        # install script program
        file_mane = os.path.join(objectxmpp.img_agent, "lib", namescript)
        logger.debug("dump file %s to %s"%(namescript, file_mane))
    if 'file_mane' in locals():
        filescript = open(file_mane, "wb")
        filescript.write(content)
        filescript.close()
        newdescriptorimage = Update_Remote_Agent(objectxmpp.img_agent)
        if newdescriptorimage.get_fingerprint_agent_base() == objectxmpp.descriptor_master['fingerprint']:
            logger.debug("RE_INSTALL AGENT VERSION %s to %s"%(file_get_contents(os.path.join(objectxmpp.img_agent, "agentversion")), objectxmpp.boundjid.bare ))
            reinstall_agent_with_image_agent_version_master(objectxmpp)
    else:
        logger.error("dump file type missing")


def search_diff_agentversion(objectxmpp, frombase, frommachine):
    listdifference = []
    listmissing = []
    for i in frombase:
        if i in frommachine:
            # fichiers des 2 cotes.
            if frommachine[i] != frombase[i]:
                listdifference.append(i)
        else:
            listmissing.append(i)
    listdifference.extend(listmissing)
    return listdifference

def search_filesupp_agentversion(objectxmpp,frommachine, frombase):
    listsupp = []
    listmissing = []
    for i in frommachine:
        if not i in frombase:
            listsupp.append(i)
    return listsupp

def delete_file_image(objectxmpp, listsuppfile):
    if 'program_agent' in listsuppfile and len(listsuppfile ['program_agent']) != 0:
        for namescript in listsuppfile ['program_agent']:
            file_mane = os.path.join(objectxmpp.img_agent, namescript)
            try:
                os.remove(file_mane)
                logger.debug("remove file  image %s"%(file_mane))
            except OSError:
                logger.warning("remove file  image %s : file not exist "%(file_mane))
    if 'lib_agent' in listsuppfile and len(listsuppfile ['lib_agent']) != 0:
        for namescript in listsuppfile ['lib_agent']:
            file_mane = os.path.join(objectxmpp.img_agent,"lib", namescript)
            try:
                os.remove(file_mane)
                logger.debug("remove file  image %s"%(file_mane))
            except OSError:
                logger.warning("remove file  image %s : file not exist "%(file_mane))
    if 'script_agent' in listsuppfile and len(listsuppfile ['script_agent']) != 0:
        for namescript in listsuppfile ['script_agent']:
            file_mane = os.path.join(objectxmpp.img_agent,"script", namescript)
            try:
                os.remove(file_mane)
                logger.debug("remove file  image %s"%(file_mane))
            except OSError:
                logger.warning("remove file  image %s : file not exist "%(file_mane))
