# -*- coding: utf-8 -*-
import sys, os, platform, json
from  lib.utils import pulginprocess
from wakeonlan import wol

plugin={"VERSION": "1.0", "NAME" :"wakeonlan","TYPE":"relayserver"}
@pulginprocess
def action( objetxmpp, action, sessionid, data, message, dataerreur,result):
    print data
    try:
        wol.send_magic_packet(data['macaddress'])
        result['data']['demarage'] = "ok"
    except:
        dataerreur['data']['msg'] = "ERROR : plugin wakeonlan"
        dataerreur['ret'] = 255
        raise

