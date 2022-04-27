==========================
Asterisk Plus Installation
==========================

.. contents::

In order to connect Asterisk and Odoo a special middleware Agent is required to be
installed on the Asterisk server. 

The Agent does the following jobs:

* Forwards Asterisk Manager Interface (AMI) events to Odoo according to the downloaded events map.
* Executes Asterisk AMI actions received from Odoo.
* Protects Asterisk from DDoS and password bruteforce attacks.(optionally, disabled by default).
* Manages the installation & upgrade process.

The most simple way to install the Agent is to use docker compose style setup but a general server
wide installation is also supported.

Below both installation methods are described.

Docker based installation
=========================
This setup assumes that both Odoo and Asterisk are already installed and running outside docker.

So in this case you should do the following steps:

* Forward Salt API port (default 48008) from your host machine to the agent container.
* Supply a configuration file for Odoo & Asterisk.
* Change the default Sapt API password.

Let review these steps in more details.

.. code::

    version: '3.1'
    services:

    agent:
        image: odoopbx/agent:1.0
        ipc: host
        # Required to manage host's ipsets (if reactor is enabled).
        privileged: true
        volumes:
        - ./minion_local.conf:/etc/salt/minion_local.conf
        - ./auth:/etc/salt/auth
        - /var/spool/asterisk:/var/spool/asterisk
        - /etc/asterisk:/etc/asterisk
        - /var/run/asterisk:/var/run/asterisk
        ports:
        - 0.0.0.0:30000:30000
        - 0.0.0.0:48008:30000
  
Before starting this file create custom ``minion_local.conf`` and ``auth`` files (see below).

Custom minion_local.conf configuration file
###########################################
Here is an example of  ``minion_local.conf``:

.. code:: yaml

    odoo_host: odoo # Put IP address or hostname here.    
    odoo_user: asterisk1 # It's ok to leave the default user name.
    odoo_password: asterisk1 # This is the default password set on addon installation. CHANGE IT here and in Odoo!!!
    odoo_db: my_database # Replace to your real Odoo database name.
    odoo_port: 8069 # If your Odoo is behind a proxy put 80 or 443 here.
    odoo_use_ssl: False # Set it to True only if Odoo is behind a proxy with HTTPS enabled.
    # Asterisk settings.
    ami_login: odoo
    ami_secret: your-ami-secret-here
    ami_port: 5038
    ami_host: asterisk.host # Your Asterisk host. Most common value is 127.0.0.1.

Change the default Salt API password
####################################
The Salt API password is stored in ``/etc/salt/auth`` file. Generate a new password like that:

.. code:: bash

  echo -n "salt-api-new-pass" | md5sum

Save this password in ``auth`` file:

.. code::

  odoo|bf67d5d35021cb370bcbfb046f6c437f

Start the Agent
###############
Now your are ready for a test run:

.. code:: sh

  docker-compose up agent

Check the output. If there is no error messages, press CTRL+C and restart the Agent in background mode:

.. code:: sh

    docker-compose up -d agent

Debug the Agent connection
##########################
Agent is built-up from three processes:

* Salt API
* Salt master
* Salt minion

The processes are started in a `tmux <https://www.hamvocke.com/blog/a-quick-and-easy-guide-to-tmux/>`__ session.

So in order to debug a process you first have to enter the container using

.. code::
  
  docker-compose exec agent bash
  
command and then re-connect to a tmux session using

.. code::
  
  tmux a

command.  After that you can switch between three consoles:

*  ``CTRL+b 0`` - the Salt master
*  ``CTRL+b 1`` - the Salt API
*  ``CTRL+b 2`` - the Salt minion

You can press ``CTRL+C`` to terminate the process and restart it in in debug mode. For example, to 
start the salt minion in debug mode go console #2 and enter:

.. code::

  CTRL+C
  salt-minion -l debug

To exit from tmux enter ``CTRL+B d``. Then you can exit the container with ``CTRL+d``.

Server wide Agent installation
==============================
This method describes how to install OdooPBX Agent on a ordinary Linux server.

System requirements
###################
OdooPBX is based mainly on Python 3. So it must be properly installed.

If you have it installed you can skip this section.

On different systems same packages have different names.

We support the most popular Linux distributions.

If something does not work for you it's ok to send us ``cat /etc/*release | mail reports@odoopbx.com`` so 
that we could add support to your system.

Ubuntu and Debian
+++++++++++++++++

.. code::

    apt update && apt -y install python3-pip python3-setproctitle

CentOS Versions 6&7
+++++++++++++++++++
First, you should enable and install Python3 and pip.

There are at least `3 ways to install the latest Python3 package on CentOS <https://www.2daygeek.com/install-python-3-on-centos-6/>`_. 

Below is one of them (IUS).

.. code:: 

    curl 'https://setup.ius.io/' -o setup-ius.sh
    sh setup-ius.sh
    yum --enablerepo=ius install python36 python36-pip python36-setproctitle

.. warning::

   Please note that if you are using FreePBX, which is based on Centos 7, it has a different Python3 naming schema,
   similar to ius, but using Sangoma's own repositories. You shouldn't try to use 3rd party repositories,
   simply run ``yum makecache`` to get latest information from Sangoma's repositories and install Python3 by running 
   ``yum install python36u python36u-pip``

CentOS Version 8
++++++++++++++++
Latest CentOS is quite ready for Python3. So here are the installation steps:

.. code::

    yum install python3 python3-pip python3-devel    


Sangoma Linux release 7.8
+++++++++++++++++++++++++

.. code::

    yum install python36u python36u-pip python36u-devel
    

Install Agent
#############
The Agent itself is built upon the Saltstack platform. 
So if you come the Salt world - welcome home, dude!

The Agent uses Salt states files to install different OdooPBX components. 

Below commands will install the Agent itself:

.. code:: sh

    pip3 install odoopbx
    salt-call state.apply agent

.. note:: 
    Please note that the Agent requires root privileges. The commands below must be run as the **root** user.

Now configure Odoo & Asterisk to use the Agent.

Odoo configuration
==================
Odoo should be configured in the right way in order to be ready for Asterisk Plus.

When the Agent is used to install Odoo all is setup automatically by it. Read below only if you have 
your own Odoo server deployed somewhere. 

Workers
#######
Workers are Odoo processes that handle requests.

Asterisk modules make many short-running requests.

So your Odoo should be configured with at least 2 workers 
(but 4 workers is the minimal recommended starting value).

.. warning:: 
    If you use odoo.sh with 1 worker configured it is possible to get issues related to performance.


Long polling
############
Internal gevent-based server must be enabled (aka long polling) for popup notifications
and live channels reload to work.

When you enable workers gevent server is also enabled.

By default port 8072 is used and you can check it with:

.. code::

    netstat -an | grep LISTEN | grep 8072

on your Odoo server.

If you don't use a proxy (apache / nginx / etc) then you should open Odoo
on gevent's port e.g.: ``http://127.0.0.1:8072/web``.

If you run Odoo behind a proxy be sure to add a different proxy handler for the ``/longpolling/poll`` URL.

Here is a snippet for Nginx:

.. code::

    location /longpolling/poll {
      proxy_pass http://127.0.0.1:8072;
    }

If you see ``Exception: bus.Bus unavailable`` in your Odoo log then it means you
did not set long polling right.

Single / multi database setup
#############################
There is one thing your should know.

It's a good configuration when your Odoo is limited to just one database with dbfilter
configuration option and list_db set to False.

But when you run Odoo with multiple databases some special configuration must be enabled.

You should add asterisk_plus to ``server_wide_modules`` parameter in order to be able 
to make CURL requests from the Asterisk dialplan (see below).

Here is an example of such a configuration line:

.. code::

    server_wide_modules = web,asterisk_plus

If your Odoo is in a single-mode setup there is no need to configure the ``server_wide_modules`` parameter.

Or follow this instruction to copy OdooPBX addons to your custom Odoo server.

Install Asterisk Plus addons in the same way you install any other Odoo module.

Do a database backup before installation or upgrade and also make a backup of previous version of the module
if you have it (just in case to be able to restore quicky).

Make sure that ``addons_path`` is set correctly to include OdooPBX addons.

The module dependencies are localed in ``requirements.txt`` file located in the addons folder.

If you use odoo.sh make sure you copy the requirements to your modules top folder so that odoo.sh can 
install the required dependencies.

If you use python virtualenv make sure you install the requirements there and not system wide.

Asterisk configuration
======================
Prepare an Asterisk Manager Interface (AMI) account to allow the Agent to connect to Asterisk.

Vanilla Asterisk requires editing the  ``manager.conf`` file, which is usually found in ``/etc/asterisk``.

A sample configuration is provided below, which lets the Agent to connect
to your Asterisk server AMI port (usually 5038) using the login ``odoo`` with the password ``odoo``.


``manager.conf``:

.. code::

    [general]
    enabled = yes
    webenabled = no ; Asterisk calls does not use HTTP interface
    port = 5038
    bindaddr = 127.0.0.1

    [odoo]
    secret=odoo
    displayconnects = yes
    read=all
    write=all
    deny=0.0.0.0/0.0.0.0
    permit=127.0.0.1/255.255.255.0

Asterisk-based distributions such as **FreePBX**  offer a web GUI interface for managing your
AMI users. You can use that interface to create one, or you can add the account configuration data in
a custom file, which will not be managed by the distro, usually ``/etc/asterisk/manager_custom.conf``

.. warning::
   For security reasons always use deny/permit options in your manager.conf.
   Change permit option to IP address of your Asterisk server if agent is not started on the same box. 

Make sure that you applied new configuration by checking the Asterisk console:

.. code::
    
    manager show user odoo


Agent configuration
===================
When Odoo & Asterisk are ready it's time to configure the Agent.

After the Agent is installed you should create ``/etc/salt/minion_local.conf`` and ``/etc/salt/auth`` 
files.(see Docker section :ref:`Custom minion_local.conf configuration file` above for examples).

To test your configuration run the Agent in the foreground:

.. code:: 

  salt-minion -l info

Check the output printed on the screen. There should be no errors on start. 
You should see messages that confirm both Odoo connection and Asterisk connection as shown below:

.. code::

   [INFO    ] salt.loaded.ext.engines.odoo_executor:48 Logged into Odoo.
   * * *
   [INFO    ] salt.loaded.ext.engines.asterisk_ami:69 AMI connecting to odoo@127.0.0.1:5038...
   [INFO    ] salt.loaded.ext.engines.asterisk_ami:72 Registering for AMI event *

Now stop it with CTRL+C and run it as a service:

.. code::

  systemctl start salt-api
  systemctl start salt-master
  systemctl start salt-minion


Asterisk Dialplan configuration
===============================

Asterisk Plus exposes additional functionality by providing the following controllers:

#. You can get the contact's name by accessing ``asterisk_plus/get_caller_name?number=${CALLERID(number)}``
#. If the Contact for the phone number has a manager set, use ``asterisk_plus/get_partner_manager?number=${CALLERID(number)}`` to get the manager's number
#. You can get the Contact's tags by using ``/asterisk_plus/get_caller_tags?number=${CALLERID(number)}``

Here are some examples of integration, using Asterisk dialplans.


``extensions.conf``:

.. code::

    [globals]
    ODOO_URL=http://odoo:8069

    ; Set connection options for curl.
    [sub-setcurlopt]
    exten => _X.,1,Set(CURLOPT(conntimeout)=3)
    exten => _X.,n,Set(CURLOPT(dnstimeout)=3)
    exten => _X.,n,Set(CURLOPT(httptimeout)=3)
    exten => _X.,n,Set(CURLOPT(ssl_verifypeer)=0)
    exten => _X.,n,Return

    ; Partner's extension click2call e.g. +1234567890##101
    [post-dial-send-dtmf]
    exten => s,1,NoOp(DTMF digits: ${dtmf_digits})
    same => n,ExecIf($["${dtmf_digits}" = ""]?Return)
    same => n,Wait(${dtmf_delay})
    same => n,SendDTMF(${dtmf_digits})
    same => n,Return


    ;Set Caller ID name from Odoo
    ; Get caller ID name from Odoo, replace odoo to your Odoo's hostname / IP address
    ; Arguments:
    ; - number: calling number, strip + if comes with +.
    ; - db: Odoo's database name, ommit if you have one db or use dbfilter.
    ; - country: 2 letters country code, See https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
    ; If country code is omitted Asterisk Agent's Odoo account's country settings will be used for phonenumbers parsing.
    
    [sub-setcallerid]
    exten => _X.,1,Gosub(sub-setcurlopt,${EXTEN},1)
    ;   You need to cut leading + on numbers incoming from trunks before passing it to get_caller_name.
    exten => _X.,n,Set(CALLERID(name)=${CURL(${ODOO_URL}/asterisk_plus/get_caller_name?number=${CALLERID(number)})})
    exten => _X.,n,Return


    ; Get partner’s manager (salesperson) channel

    [sub-dialmanager]
    exten => _X.,1,Set(manager_channel=${CURL(${ODOO_URL}/asterisk_plus/get_partner_manager?number=${CALLERID(number)})})
    exten => _X.,n,ExecIf($["${manager_channel}" != ""]?Dial(${manager_channel}/${EXTEN},60,t))
    exten => _X.,n,Return
    
    ; Get partner's tags to create a special call routing (e.g. VIP queue)
    ; You can also get caller tags from Odoo with the following controller Here is an example:
    
    ; Partner tags
    ; VIP - tag name in this example.

    [partner-vip-tag-lookup] 
    exten => _X.,1,Set(CURLOPT(conntimeout)=3)
    exten => _X.,n,Set(CURLOPT(dnstimeout)=3)
    exten => _X.,n,Set(CURLOPT(httptimeout)=3)
    exten => _X.,n,Set(CURLOPT(ssl_verifypeer)=0)
    exten => _X.,n,Set(tags=${CURL(${ODOO_URL}/asterisk_plus/get_caller_tags?number=${CALLERID(number)})})
    exten => _X.,n,NoOp(Tags: ${tags})
    exten => _X.,n,Set(match=${REGEX("VIP" ${tags})})
    exten => _X.,n,NoOp(Match: ${match})
    exten => _X.,n,Return(${match})

    ; Check VIP tag
    [check-vip]
    exten => _X.,1,Gosub(partner-vip-tag-lookup,${EXTEN},1,VIP)
    exten => _X.,n,GotoIf($["${GOSUB_RETVAL}" = "1"]?vip-queue,${EXTEN},1)


    ; Incoming call handling

    [from-sip-external]    
    exten => _X.,1,Gosub(sub-setcallerid,${EXTEN},1) ; Set partner's caller name    
    exten => _X.,n,MixMonitor(${UNIQUEID}.wav) ; Record call    
    exten => _X.,n,Gosub(sub-dialmanager,${EXTEN},1) ; Try to connect to manager
    ; Put here some login to handle if manager channel is busy for example put in the queue.
    exten => _X.,n,Queue(sales)

    [from-internal]
    exten => _X.,1,MixMonitor(${UNIQUEID}.wav) ; Activate call recording.
    exten => _XXXX,2,Dial(SIP/${EXTEN},30) ; Local users calling    
    exten => _XXXXX.,2,Dial(SIP/provider/${EXTEN},30,TU(post-dial-send-dtmf) ; Outgoing calls pattern


FreePBX notes
=============
FreePBX has external callerid support. Please refer to FreePBX documentation for more details.


Additional support
==================
Please note that only paid installations are supported by our team.

In order to receive support, please submit your request here: https://odoopbx.com/contactus. Please provide there your purchase order number and date.

We also offer PBX server installation and maintenance. Please `contact <https://odoopbx.com/contactus>`__ us for more details.

