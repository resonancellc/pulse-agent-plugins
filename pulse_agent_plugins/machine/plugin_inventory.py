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

from  lib.utils import pluginprocess
import sys, os
from  lib.utils import simplecommand
import zlib, base64
import traceback


plugin={"VERSION": "1.0", "NAME" :"inventory", "TYPE":"machine"}


@pluginprocess
def action( objetxmpp, action, sessionid, data, message, dataerreur, result):
    print "plugin_inventory"
    if sys.platform.startswith('linux'):
        try:
            obj = simplecommand("fusioninventory-agent  --stdout > /tmp/inventory.txt")
            Fichier = open("/tmp/inventory.txt",'r')
            result['data']['inventory'] = Fichier.read()
            Fichier.close()
            result['data']['inventory'] = base64.b64encode(zlib.compress(result['data']['inventory'],9))
        except Exception, e:
            print "Error: %s" % str(e)
            traceback.print_exc(file=sys.stdout)
            raise
    elif sys.platform.startswith('win'):
        try:
            program = os.path.join(os.environ["ProgramFiles"],'FusionInventory-Agent','fusioninventory-agent.bat')
            namefile = os.path.join(os.environ["ProgramFiles"], 'Pulse', 'tmp', 'inventory.txt')
            cmd = """\"%s\" --local=\"%s\""""%(program,namefile)

            Fichier = open(namefile,'r')
            result['data']['inventory'] = base64.b64encode(zlib.compress(Fichier.read(), 9))
            Fichier.close()
        except Exception, e:
            print "Error: %s" % str(e)
            traceback.print_exc(file=sys.stdout)
            raise
    elif sys.platform.startswith('darwin'):
        pass
