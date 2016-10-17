# -*- coding: utf-8 -*-
import json

from lib.utils import  simplecommandestr, simplecommande
import sys, os, platform
from  lib.utils import pulginprocess
from lxml import etree
import MySQLdb
import traceback
plugin={"VERSION": "1.0", "NAME" :"guacamoleconf", "TYPE":"relayserver"}


def insertprotocole(protocole, hostname):
    return """INSERT INTO guacamole_connection (connection_name, protocol) VALUES ( '%s_%s', '%s');"""%(protocole.upper(), hostname, protocole.lower())

def deleteprotocole(protocole, hostname):
    return """DELETE FROM `guacamole_connection` WHERE connection_name = '%s_%s';"""%(protocole.upper(),hostname)

def insertparameter(id, parameter, value):
    return """INSERT INTO guacamole_connection_parameter (connection_id, parameter_name, parameter_value) VALUES (%s, '%s', '%s');"""%(id,parameter,value)

@pulginprocess
def action( objetxmpp, action, sessionid, data, message, dataerreur,result):
    
    # print objetxmpp.config
    # Open database connection
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

    try:
        #delete connection
        for proto in protos:
            cursor.execute(deleteprotocole(proto, data['hostname']))
            db.commit()
        #create connection
        for proto in protos:
            result['data']['connection'][proto.upper()] = -1
            cursor.execute(insertprotocole(proto, data['hostname']))
            db.commit()
            result['data']['connection'][proto.upper()] = cursor.lastrowid
    except MySQLdb.Error, e:
        db.close()
        dataerreur['data']['msg'] = "MySQL Error: %s" % str(e)
        traceback.print_exc(file=sys.stdout)
        raise
    except Exception, e:
        dataerreur['data']['msg'] = "MySQL Error: %s" % str(e)
        traceback.print_exc(file=sys.stdout)
        db.close()
        raise
    ###################################
    ##configure parameters
    ###################################
    try:
        for proto in protos:
            if proto == 'rdp':
                port = '3389'
            elif proto == 'ssh':
                port = '22'
            else:
                port = '5901'
            cursor.execute(insertparameter(result['data']['connection'][proto.upper()], 'hostname', data['machine_ip']))
            db.commit()
            cursor.execute(insertparameter(result['data']['connection'][proto.upper()], 'port', port))
            db.commit()
            cursor.execute(insertparameter(result['data']['connection'][proto.upper()], 'color-depth', '24'))
            db.commit()
    except MySQLdb.Error, e:
        db.close()
        dataerreur['data']['msg'] = "MySQL Error: %s" % str(e)
        traceback.print_exc(file=sys.stdout)
        raise
    except Exception, e:
        dataerreur['data']['msg'] = "MySQL Error: %s" % str(e)
        traceback.print_exc(file=sys.stdout)
        db.close()
        raise
    db.close()
