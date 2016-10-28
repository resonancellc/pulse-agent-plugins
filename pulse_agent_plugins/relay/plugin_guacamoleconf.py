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

import sys
from  lib.utils import pluginprocess
import MySQLdb
import traceback
plugin={"VERSION": "1.0", "NAME" :"guacamoleconf", "TYPE":"relayserver"}

def insertprotocol(protocol, hostname):
    return """INSERT INTO guacamole_connection (connection_name, protocol) VALUES ( '%s_%s', '%s');"""%(protocol.upper(), hostname, protocol.lower())

def deleteprotocol(protocol, hostname):
    return """DELETE FROM `guacamole_connection` WHERE connection_name = '%s_%s';"""%(protocol.upper(),hostname)

def insertparameter(id, parameter, value):
    return """INSERT INTO guacamole_connection_parameter (connection_id, parameter_name, parameter_value) VALUES (%s, '%s', '%s');"""%(id,parameter,value)

@pluginprocess
def action( objetxmpp, action, sessionid, data, message, dataerreur,result):
    try:
        db = MySQLdb.connect(   host=objetxmpp.config.guacamole_dbhost,
                                user=objetxmpp.config.guacamole_dbuser,
                                passwd=objetxmpp.config.guacamole_dbpasswd,
                                db=objetxmpp.config.guacamole_dbname )
    except Exception as e:
        dataerreur['data']['msg'] = "MySQL Error: %s" % str(e)
        traceback.print_exc(file=sys.stdout)
        raise
    cursor=db.cursor()
    result['data']['uuid'] = data['uuid']
    result['data']['connection'] = {}

    protos = ['rdp','ssh','vnc']

    #delete connection
    for proto in protos:
        try:
            cursor.execute(deleteprotocol(proto, data['hostname']))
            db.commit()
        except:
            pass

    #create connection
    for proto in data['remoteservice']:
        if data['remoteservice'][proto] !="":
            try: 
                result['data']['connection'][proto.upper()] = -1
                cursor.execute(insertprotocol(proto, data['hostname']))
                db.commit()
                result['data']['connection'][proto.upper()] = cursor.lastrowid
            except MySQLdb.Error, e:
                dataerreur['data']['msg'] = "MySQL Error: %s" % str(e)
                traceback.print_exc(file=sys.stdout)
            except Exception, e:
                dataerreur['data']['msg'] = "MySQL Error: %s" % str(e)
                traceback.print_exc(file=sys.stdout)
    ###################################
    ##configure parameters
    ###################################
    for proto in data['remoteservice']:
        if data['remoteservice'][proto] !="":
            try:
                port = data['remoteservice'][proto]
                cursor.execute(insertparameter(result['data']['connection'][proto.upper()], 'hostname', data['machine_ip']))
                db.commit()
                cursor.execute(insertparameter(result['data']['connection'][proto.upper()], 'port', port))
                db.commit()
                cursor.execute(insertparameter(result['data']['connection'][proto.upper()], 'color-depth', '24'))
                db.commit()
            except MySQLdb.Error, e:
                dataerreur['data']['msg'] = "MySQL Error: %s" % str(e)
                traceback.print_exc(file=sys.stdout)
            except Exception, e:
                dataerreur['data']['msg'] = "MySQL Error: %s" % str(e)
                traceback.print_exc(file=sys.stdout)
    db.close()
    
