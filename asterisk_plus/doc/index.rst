==========================
Asterisk Plus Installation
==========================

.. contents::

In order to connect Asterisk and Odoo a special middleware Agent is required to be
installed on the Asterisk server.  The source of this file is located at our Documenation - https://docs.odoopbx.com/install/docker.html.

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

* Open on firewall Salt API port (default 48008) and WEB CLI port (default 30000).
* Supply a configuration file for Odoo & Asterisk.
* Change the default Sapt API password.

Let review these steps in more details.

.. code::

    version: '3.1'
    services:

  pbx:
    hostname: pbx
    image: odoopbx/pbx
    network_mode: host
    # Required to manage host's ipsets (if reactor is enabled).
    privileged: true
    environment:
      - ASTERISK_AUTOSTART=false
    volumes:
      - ./minion_local.conf:/etc/salt/minion_local.conf
      - ./auth:/etc/salt/auth
      - /var/spool/asterisk:/var/spool/asterisk
      - /etc/asterisk:/etc/asterisk
      - /var/run/asterisk:/var/run/asterisk
  
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
    ami_host: localhost # Your Asterisk host. Most common value is 127.0.0.1.

Change the default Salt API password
####################################
The Salt API password is stored in ``/etc/salt/auth`` file. Generate a new password like that:

.. code:: bash

  echo -n "salt-api-new-pass" | md5sum

Save this password in ``auth`` file:

.. code::

  odoo|bf67d5d35021cb370bcbfb046f6c437f

Now your are ready for a test run:

.. code:: sh

  docker-compose up pbx

Check the output. If there is no error messages, press CTRL+C and restart the Agent in background mode:

.. code:: sh

    docker-compose up -d pbx

Debug the Agent connection
##########################
Agent is built-up from three processes:

* Salt API
* Salt master
* Salt minion

The processes are started by the Supervisor daemon.

So in order to debug a process you first have to enter the container using

.. code::
  
  docker-compose exec pbx bash

Now stop the required process. Usually we want to debug the salt-minion process so we stop it and
run in debug mode:  

.. code::
  
  supervisorctl stop salt-minion
  salt-minion -l debug

You can press ``CTRL+C`` to terminate the process and restart again in normal mode:
.. code::

  CTRL+C
  supervisorctl stort salt-minion

Then you can exit the container with ``CTRL+d``.

Asterisk Dialplan configuration
===============================

Asterisk Plus exposes additional functionality by providing the following controllers:

#. You can get the contact's name by accessing ``asterisk_plus/get_caller_name``
#. If the Contact for the phone number has a manager set, use ``asterisk_plus/get_partner_manager`` to get the manager's number.
#. You can get the Contact's tags by using ``/asterisk_plus/get_caller_tags``

Here are some examples of integration, using Asterisk dialplans.
`Here <https://github.com/odoopbx/agent/blob/master/salt/asterisk/files/configs/extensions.conf>`__ is 
the latest version of the below example.

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

