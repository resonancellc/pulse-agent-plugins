from setuptools import setup, find_packages

import os
import sys
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
    version='0.1',
    description = 'XMPP Agent plugins for pulse',
    url='https://www.siveo.net/',
    packages=[],
    test_suite='',
    package_data={},
    data_files=[(path + '/pulse_xmpp_agent/relay', ['pulse_agent_plugins/relay/plugin_guacamoleconf.py', 'pulse_agent_plugins/relay/plugin_wakeonlan.py']),(path + '/pulse_xmpp_agent/machine', ['pulse_agent_plugins/common/plugin_applicationdeployment.py', 'pulse_agent_plugins/common/plugin_installplugin.py', 'pulse_agent_plugins/common/plugin_restartbot.py', 'pulse_agent_plugins/common/plugin_shellcommand.py']), (path + '/pulse_xmpp_agent/relay', ['pulse_agent_plugins/common/plugin_applicationdeployment.py', 'pulse_agent_plugins/common/plugin_installplugin.py', 'pulse_agent_plugins/common/plugin_restartbot.py', 'pulse_agent_plugins/common/plugin_shellcommand.py']) ],
    entry_points={},
    extras_require={},
    install_requires=[],
    )

