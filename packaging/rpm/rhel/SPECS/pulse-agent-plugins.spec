%define tarname		pulse-agent-plugins
%define git                    SHA
%define use_git         1

Summary:	Pulse Agent Plugins
Name:		pulse-agent-plugins
Version:	1.12
%if ! %use_git
Release:        20%{?dist}
%else
Release:        20.%git.1%{?dist}
%endif
Source0:        %name-%version.tar.gz
License:	MIT
Group:		Development/Python
Url:		http://www.siveo.net
BuildArch:	noarch
BuildRequires:	python-setuptools
BuildRequires:	python-sphinx

%description
Pulse Agent Plugins

#--------------------------------------------------------------------

%package -n pulse-xmppmaster-agentplugins
Summary:    Console agent
Group:      System/Servers
Requires:   python-netifaces
Requires:   python-sleekxmpp

Conflicts:  pulseagent-plugins-relay <= 1.11-20.git20190514173147.4bbbc13e.1.1

%description -n pulse-xmppmaster-agentplugins
plugins for pulse xmppmaster

%files -n pulse-xmppmaster-agentplugins
%_var/lib/pulse2/xmpp_baseplugin
%_var/lib/pulse2/xmpp_basepluginscheduler
%_var/lib/pulse2/clients/config/
%_var/lib/pulse2/clients/config/inventory.ini.in
%_var/lib/pulse2/clients/config/applicationdeploymentjson.ini.in
%_var/lib/pulse2/clients/config/guacamole.ini.in
%_var/lib/pulse2/clients/config/reverse_ssh_on.ini.in
%python2_sitelib/pulse_agent_plugins-%{version}-py2.7.egg-info

#--------------------------------------------------------------------

%package -n pulseagent-plugins-relay
Summary:    Console agent
Group:      System/Servers
Requires:   python-wakeonlan
Requires:   python-netifaces
Requires:   python-sleekxmpp
Requires:   lsof

%description -n pulseagent-plugins-relay
plugins for pulse xmppmaster

%files -n pulseagent-plugins-relay
%python2_sitelib/pulse_xmpp_agent/pluginsrelay
%python2_sitelib/pulse_xmpp_agent/descriptor_scheduler_relay
%_var/lib/pulse2/clients/config/
%_var/lib/pulse2/clients/config/guacamoleconf.ini.in
%_var/lib/pulse2/clients/config/downloadfile.ini.in
%_var/lib/pulse2/clients/config/downloadfileexpert.ini.in

#--------------------------------------------------------------------

%package -n pulseagent-plugins-machine
Summary:    Console agent
Group:      System/Servers
Requires:   python-netifaces
Requires:   python-sleekxmpp

%description -n pulseagent-plugins-machine
plugins for pulse xmppmaster

%files -n pulseagent-plugins-machine
%python2_sitelib/pulse_xmpp_agent/pluginsmachine
%python2_sitelib/pulse_xmpp_agent/descriptor_scheduler_machine

#--------------------------------------------------------------------

%prep
%setup -q

# Remove bundled egg-info
rm -rf %{tarname}.egg-info

%build
%py2_build

%install
%py2_install

mkdir -p %buildroot%_var/lib/pulse2/xmpp_baseplugin
cp -frv pulse_agent_plugins/common/* %buildroot%_var/lib/pulse2/xmpp_baseplugin
cp -frv pulse_agent_plugins/machine/* %buildroot%_var/lib/pulse2/xmpp_baseplugin
cp -frv pulse_agent_plugins/relay/* %buildroot%_var/lib/pulse2/xmpp_baseplugin


mkdir -p %buildroot%_var/lib/pulse2/xmpp_basepluginscheduler

mkdir -p %buildroot%_var/lib/pulse2/clients/config
cp pulse_agent_plugins/config/guacamoleconf.ini.in %buildroot%_var/lib/pulse2/clients/config
cp pulse_agent_plugins/config/downloadfile.ini.in %buildroot%_var/lib/pulse2/clients/config
cp pulse_agent_plugins/config/downloadfileexpert.ini.in %buildroot%_var/lib/pulse2/clients/config
cp pulse_agent_plugins/config/inventory.ini.in %buildroot%_var/lib/pulse2/clients/config
cp pulse_agent_plugins/config/applicationdeploymentjson.ini.in %buildroot%_var/lib/pulse2/clients/config
cp pulse_agent_plugins/config/guacamole.ini.in %buildroot%_var/lib/pulse2/clients/config
cp pulse_agent_plugins/config/reverse_ssh_on.ini.in %buildroot%_var/lib/pulse2/clients/config

rm -fv %buildroot%_var/lib/pulse2/xmpp_baseplugin/plugin_updateagent.py
