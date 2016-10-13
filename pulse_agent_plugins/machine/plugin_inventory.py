# -*- coding: utf-8 -*-
from  lib.utils import pulginprocess
import sys, os
from  lib.utils import file_get_content, file_put_content, typelinux, servicelinuxinit, isprogramme, simplecommande, simplecommandestr, CreateWinUser

plugin={"VERSION": "1.0", "NAME" :"inventory", "TYPE":"machine"}


@pulginprocess
def action( objetxmpp, action, sessionid, data, message, dataerreur, result):
    result['base64'] = True
    if sys.platform.startswith('linux'):
        pass
    elif sys.platform.startswith('win'):
        pass
    elif sys.platform.startswith('darwin'):
        pass

