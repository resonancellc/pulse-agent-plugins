#
# (c) 2016-2017 siveo, http://www.siveo.net
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

from setuptools import setup
from distutils.sysconfig import get_python_lib
import sys
import os

path = get_python_lib() ;

if sys.platform.startswith('linux'):
    confpath = os.path.join("/", "etc", "pulse-xmpp-agent")
elif sys.platform.startswith('win'):
    confpath = os.path.join(os.environ["ProgramFiles"], "Pulse", "etc")
elif sys.platform.startswith('darwin'):
    confpath = os.path.join("/", "Library", "Application Support", "Pulse", "etc")

setup(
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='pulse agent plugins',
    name='pulse_agent_plugins',
    version='1.7',
    debian_distro='stretch',
    description = 'XMPP Agent plugins for pulse',
    url='https://www.siveo.net/',
    packages=[],
    test_suite='',
    package_data={},
    data_files=[(path + '/pulse_xmpp_agent/pluginsrelay', ['pulse_agent_plugins/relay/plugin_resultsetkeypubliconauthorizedkeys.py', 'pulse_agent_plugins/relay/plugin_guacamoleconf.py', 'pulse_agent_plugins/relay/plugin_wakeonlan.py', 'pulse_agent_plugins/relay/plugin_rsapplicationdeploymentjson.py', 'pulse_agent_plugins/relay/plugin_cluster.py']),
    (path + '/pulse_xmpp_agent/pluginsmachine', ['pulse_agent_plugins/machine/plugin_inventory.py', 'pulse_agent_plugins/machine/plugin_setkeypubliconauthorizedkeys.py','pulse_agent_plugins/machine/plugin_kiosk.py']),
    (path + '/pulse_xmpp_agent/pluginsmachine', ['pulse_agent_plugins/common/plugin_enddeploy.py', 'pulse_agent_plugins/common/plugin_applicationdeploymentjson.py', 'pulse_agent_plugins/common/plugin_installplugin.py', 'pulse_agent_plugins/common/plugin_requestinfo.py', 'pulse_agent_plugins/common/plugin_restartbot.py', 'pulse_agent_plugins/common/plugin_shellcommand.py', 'pulse_agent_plugins/common/plugin_asynchromeremoteshell.py', 'pulse_agent_plugins/common/plugin_downloadfile.py', 'pulse_agent_plugins/common/plugin_guacamole.py', 'pulse_agent_plugins/common/plugin_installkey.py', 'pulse_agent_plugins/common/plugin_installpluginscheduled.py', 'pulse_agent_plugins/common/plugin_resultapplicationdeploymentjson.py', 'pulse_agent_plugins/common/plugin_reverse_ssh_on.py', 'pulse_agent_plugins/common/plugin_asynchroremoteQA.py']),
    (path + '/pulse_xmpp_agent/pluginsrelay', ['pulse_agent_plugins/common/plugin_enddeploy.py', 'pulse_agent_plugins/common/plugin_applicationdeploymentjson.py', 'pulse_agent_plugins/common/plugin_installplugin.py', 'pulse_agent_plugins/common/plugin_requestinfo.py', 'pulse_agent_plugins/common/plugin_restartbot.py', 'pulse_agent_plugins/common/plugin_shellcommand.py', 'pulse_agent_plugins/common/plugin_asynchromeremoteshell.py', 'pulse_agent_plugins/common/plugin_downloadfile.py', 'pulse_agent_plugins/common/plugin_guacamole.py', 'pulse_agent_plugins/common/plugin_installkey.py', 'pulse_agent_plugins/common/plugin_installpluginscheduled.py', 'pulse_agent_plugins/common/plugin_resultapplicationdeploymentjson.py', 'pulse_agent_plugins/common/plugin_reverse_ssh_on.py', 'pulse_agent_plugins/common/plugin_asynchroremoteQA.py']),
    (path + '/pulse_xmpp_agent/descriptor_scheduler_machine', ['pulse_agent_plugins/machine/scheduling_inv.py', 'pulse_agent_plugins/machine/scheduling_logsrotation.py']),
    (path + '/pulse_xmpp_agent/descriptor_scheduler_relay', ['pulse_agent_plugins/relay/scheduling_wsusscn2.py']),
    (path + '/pulse_xmpp_agent/descriptor_scheduler_machine', ['pulse_agent_plugins/common/scheduling_deploy.py']),
    (path + '/pulse_xmpp_agent/descriptor_scheduler_relay', ['pulse_agent_plugins/common/scheduling_deploy.py'])],
    entry_points={},
    extras_require={},
    install_requires=[],
    )
