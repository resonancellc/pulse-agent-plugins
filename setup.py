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

path = get_python_lib() ;

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
    version='1.1',
    description = 'XMPP Agent plugins for pulse',
    url='https://www.siveo.net/',
    packages=[],
    test_suite='',
    package_data={},
    data_files=[(path + '/pulse_xmpp_agent/pluginsrelay', ['pulse_agent_plugins/relay/plugin_guacamoleconf.py', 'pulse_agent_plugins/relay/plugin_wakeonlan.py','pulse_agent_plugins/relay/plugin_rsapplicationdeploymentjson.py']),(path + '/pulse_xmpp_agent/pluginsmachine',['pulse_agent_plugins/machine/plugin_inventory.py','pulse_agent_plugins/machine/plugin_applicationdeploymentjson.py',]),(path + '/pulse_xmpp_agent/pluginsmachine', ['pulse_agent_plugins/machine/plugin_applicationdeploymentjson.py', 'pulse_agent_plugins/common/plugin_installplugin.py', 'pulse_agent_plugins/common/plugin_restartbot.py', 'pulse_agent_plugins/common/plugin_shellcommand.py']),(path + '/pulse_xmpp_agent/pluginsrelay', ['pulse_agent_plugins/machine/plugin_applicationdeploymentjson.py', 'pulse_agent_plugins/common/plugin_installplugin.py','pulse_agent_plugins/common/plugin_restartbot.py', 'pulse_agent_plugins/common/plugin_shellcommand.py']) ],
    entry_points={},
    extras_require={},
    install_requires=[],
    )

