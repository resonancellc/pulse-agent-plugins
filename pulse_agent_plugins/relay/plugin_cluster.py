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
# file : pulse_agent_plugins/relay/plugin_cluster.py
import json
import logging
logger = logging.getLogger()


def MsgToContributorCluster(countsessiondeploy):
    #create message
    return {
                "data" : { "numbersession" : countsessiondeploy
                }
            }

DEBUGPULSEPLUGIN = 25

plugin = { "VERSION" : "1.0", "NAME" : "cluster", "TYPE" : "relayserver", "DESC" : "update list ARS cluster" }

def action( objectxmpp, action, sessionid, data, message, dataerreur):
    logging.getLogger().info("call %s from %s"%(plugin,message['from']))
    # print json.dumps(data, indent = 4)
    if "subaction" in data:
        if data['subaction'] == "initclusterlist":
            # update list cluster jid
            jidclusterlistrelayservers = [jidrelayserver for jidrelayserver in data['data'] if jidrelayserver != message['to']]

            datacluster = MsgToContributorCluster(objectxmpp.session.getcountsession())

            # delete reference ARS si pas dans jidclusterlistrelayservers
            for ars in jidclusterlistrelayservers:
                if not ars in objectxmpp.jidclusterlistrelayservers:
                    objectxmpp.jidclusterlistrelayservers[ars] = { 'numbersession' : 0 }


            for ars in objectxmpp.jidclusterlistrelayservers:
                if not ars in jidclusterlistrelayservers:
                    del objectxmpp.jidclusterlistrelayservers[ars]
                result = {
                                'action': "%s"%action,
                                'sessionid': sessionid,
                                "subaction" : "refreshload",
                                'data' : datacluster,
                                'ret' : 0,
                                'base64' : False
                    }
                objectxmpp.send_message( mto=message['from'],
                                mbody=json.dumps(result),
                                mtype='chat')

        elif data['subaction'] == "refreshload":
            print "refrehload"

    result = {
                'action': "result%s"%action,
                'sessionid': sessionid,
                'data' : {},
                'ret' : 0,
                'base64' : False }

    logging.getLogger().debug("new ARS list friend of cluster : %s"% objectxmpp.jidclusterlistrelayservers)

    #message
    objectxmpp.send_message( mto=message['from'],
                             mbody=json.dumps(result),
                             mtype='chat')
