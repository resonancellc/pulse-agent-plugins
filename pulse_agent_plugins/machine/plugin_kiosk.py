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
# file pulse_xmpp_agent/pluginsmachine/plugin_kiosk.py

import logging
import json
import traceback
import sys
import socket

plugin = {"VERSION": "1.3", "NAME" : "kiosk", "TYPE" : "machine"}

def action(objectxmpp, action, sessionid, data, message, dataerreur):
    logging.getLogger().debug("=====================================================")
    logging.getLogger().debug(plugin)
    logging.getLogger().debug("=====================================================")

    datasend = {'action' : "result%s"%plugin['NAME'],
                'data' :{'subaction' : 'test'},
                'sessionid' : sessionid
               }
    try:
        if data['subaction'] == 'test':
            datasend['data']['msg'] = "test success"
            objectxmpp.send_message(mto=message['from'],
                                    mbody=json.dumps(datasend, sort_keys=True, indent=4),
                                    mtype='chat')
        elif data['subaction'] == 'listpackage':
            # todo
            pass
        elif data['subaction'] == 'initialisation_kiosk':
            #if len(data['data']) != 0:
            print "send to kiosk"
            strjson = json.dumps(data['data'])
            send_kiosk_data(strjson, objectxmpp.config.kiosk_local_port, objectxmpp, dataerreur, message)
            pass
        elif data['subaction'] == "profiles_updated":
            logging.getLogger().info("send updated profiles to kiosk")
            strjson = json.dumps(data['data'])
            send_kiosk_data(strjson, objectxmpp.config.kiosk_local_port, objectxmpp, dataerreur, message)
            pass
        elif data['subaction'] == "profiles_updated":
            logging.getLogger().info("send updated profiles to kiosk")
            strjson = json.dumps(data['data'])
            send_kiosk_data(strjson , objectxmpp.config.kiosk_local_port, objectxmpp, dataerreur, message)
            pass

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        dataerreur['ret'] = -255
        dataerreur['data']['msg'] = "plugin kiosk error on machine %s [%s]"%(objectxmpp.boundjid.bare, str(e))
        objectxmpp.send_message(mto=message['from'],
                                mbody=json.dumps(dataerreur),
                                mtype='chat')

def send_kiosk_data(datastrdata, port = 8766, objectxmpp= None, dataerror = None, message = None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('localhost', port)
    try:
        sock.connect(server_address)
        print "send message"
        sock.sendall(datastrdata.encode('ascii'))
        data = sock.recv(2048)
        print ('received "%s"' % data)
    except Exception as e:
        dataerror['ret'] = -255
        if not "Errno 111" in str(e):
            traceback.print_exc(file=sys.stdout)
            logging.getLogger().error("Kiosk [%s]"%str(e))
            dataerror['data']['msg'] = "plugin kiosk error on machine %s : [%s]"%(objectxmpp.boundjid.bare, str(e))
            objectxmpp.send_message(mto=message['from'],
                                    mbody=json.dumps(dataerror),
                                    mtype='chat')
        else :
            logging.getLogger().warning("Kiosk is not listen: verify presence kiosk")
            msg = "Kiosk is not listen on machine %s : [%s]\nverrify presence kiosk"%(objectxmpp.boundjid.bare, str(e))
            if objectxmpp is not None and dataerror is not None and message is not None:
                dataerror['ret'] = -255
                dataerror['data']['msg'] = msg
                objectxmpp.send_message(mto=message['from'],
                                        mbody=json.dumps(dataerror),
                                        mtype='chat')

    finally:
        sock.close()
