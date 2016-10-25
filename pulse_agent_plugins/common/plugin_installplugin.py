# -*- coding: utf-8 -*-

import os

plugin={"VERSION": "1.0", "NAME" : "installplugin", "TYPE" : "all"}

def action( objetxmpp, action, sessionid, data, message, dataerreur ):
    if action == 'installplugin':
        if len(data) != 0 :
            namefile =  os.path.join(objetxmpp.config.pathplugins, data['pluginname'])

            try:
                fileplugin = open(namefile, "w")
                fileplugin.write(str(data['datafile']))
                fileplugin.close()
            except :
                print "Error: cannor write on file"
                return
            msg = "install plugin %s on %s"%(data['pluginname'],message['to'].user)
            objetxmpp.loginformation(msg)
