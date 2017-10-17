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
import MySQLdb
import traceback
import sys

plugin = {"VERSION" : "1.0", "NAME" : "guacamole",  "TYPE" : "relayserver"}


def action( xmppobject, action, sessionid, data, message, dataerreur ):
    print data

    # Get reversessh remote port and run reverse_ssh_on
    try:
        db = MySQLdb.connect(host=xmppobject.config.guacamole_dbhost,
                             user=xmppobject.config.guacamole_dbuser,
                             passwd=xmppobject.config.guacamole_dbpasswd,
                             db=xmppobject.config.guacamole_dbname)
        cursor = db.cursor()
        sql = """ SELECT parameter_value FROM guacamole_connection_parameter WHERE connection_id = %s AND parameter_name = 'port';"""%(data['cux_id'])
        cursor.execute(sql)
        results = cursor.fetchall()
        localport = results[0][0]
        if data['cux_type'] == 'SSH':
            remoteport = 22
        elif data['cux_type'] == 'RDP':
            remoteport = 3389
        elif data['cux_type'] == 'VNC':
            remoteport = 5900

    except Exception as e:
        db.close()
        dataerreur['data']['msg'] = "MySQL Error: %s" % str(e)
        traceback.print_exc(file=sys.stdout)
        raise

    datareversessh = {
            'action': 'reverse_ssh_on',
            'sessionid': sessionid,
            'data' : {
                    'request' : 'askinfo',
                    'port' : localport,
                    'host' : data['uuid'],
                    'remoteport' : remoteport,
                    'reversetype' : 'R',
                    'options' : 'createreversessh'
            },
            'ret' : 0,
            'base64' : False }
    xmppobject.send_message(mto = message['to'],
                mbody = json.dumps(datareversessh),
                mtype = 'chat')
    return
