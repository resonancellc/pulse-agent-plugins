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
from  lib.utils import pulginprocess
from  lib.utils import simplecommand

plugin={"VERSION": "1.0", "NAME" :"shellcommand", "TYPE":"all"}

# le decorateur @pulginprocess
# defini squelette du dict result sectionid action et ret definie
# se charge d'envoyé message result si pas d'exception ou dict erreur si exception
# le code de retour est 8 par default si erreur sinon redefinissait le code d'erreur result['ret']=numerreur
# le message d'erreur par default est "ERROR : %s"%action  sinon redefinir le message d'erreur
# data est directement utilisable meme si celui ci était passé en base64.
# si vous voulez que data soit en base 64 lors de l'envoi definiser result['base64'] = True

@pulginprocess
def action( objetxmpp, action, sessionid, data, message, dataerreur, result):
    obj = simplecommand(data['cmd'])
    for i in range(len(obj['result'])):
        obj['result'][i]=obj['result'][i].rstrip('\n')
    a = "\n".join(obj['result'])
    dataerreur['ret'] = obj['code']
    if obj['code'] == 0:
        result['data']['result'] = a
    else:
        dataerreur['data']['msg']="Erreur commande\n %s"%a
        raise
