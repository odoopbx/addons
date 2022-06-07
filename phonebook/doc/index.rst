===============================================
 Phonebook documentation
===============================================

.. contents::
   :depth: 4

Installation & Configuration
----------------------------
If your installation is a single db (using db_filter) you have to do nothing.

If you have many databases then add *phonebook* to your *server_wide_modules* setting, e.g.:

.. code::

  ; for Odoo 9 and 10
  server_wide_modules=web,web_kanban,phonebook
  ; For Odoo 11 and 12
  server_wide_modules=web,phonebook

Settings
++++++++
Activate *Developer mode* and  go to *Settings -> Technical -> Parameters -> Phonebook*.

Adjust settings for your environment.


Usage
-----
Open your phone settings and set XML phonebook URL.
URL is made of your Odoo server address, db name and phone model.

Let demonstrate it with the following example.

* Odoo server address: http://my.odoo.com:8069
* Database name: demo
* Phone model: Grandstream

For single Odoo db installation (db_filter is used) the following URL is constructed:

* http://my.odoo.com:8069/phonebook/gs/phonebook.xml

For multi database Odoo environments database should be injected in the path:

* http://my.odoo.com:8069/phonebook/demo/gs/phonebook.xml (note *demo* in the path)

Aastra
++++++
Aastra phones download CSV file with contacts via TFTP. So with Aastra phones you should 
setup a cron script to periodically update file with contacts. Example:

.. code:: 

  curl -o phonebook.csv  http://my.odoo.com:8069/phonebook/demo/aastra/phonebook.csv


Atcom
+++++
Atcom phones support HTTP phonebook feature. Example URL: 
http://my.odoo.com:8069/phonebook/demo/atcom/phonebook.xml

Audiocodes
+++++
The Configuration file can include a link to a user-defined Corporate Directory
file, using the 'provisioning/corporate_directory_uri' parameter.

For example: *provisioning/corporate_directory_uri=phonebook.csv*

You need to create a cron script to periodically reload the phonebook from Odoo and
put it into provisioning folder. 

Example:

.. code:: 

  curl -o phonebook.csv  http://my.odoo.com:8069/phonebook/demo/audiocodes/phonebook.csv


Cisco
+++++
Example URL: http://my.odoo.com:8069/phonebook/demo/cisco/phonebook.xml

Digium A-Series
+++++++++++++++
Remote retrieval, as a part of the phone's configuration file, 
is controlled with the *AUTOUPDATE CONFIG MODULE* configuration section with the 
Auto Pbook Url configuration parameter, e.g.:

.. code::

    <<VOIP CONFIG FILE>>Version:2.0000000000
    <AUTOUPDATE CONFIG MODULE>
    Auto Pbook Url     :http://my.odoo.com:8069/phonebook/demo/digium_a/phonebook.xml
    <<END OF FILE>>

Digium D-Series
+++++++++++++++
Contacts files that the phone should load are separate files, defined by DPMA or 
configured in the phone's main configuration XML file. 
For DPMA, Contacts files are specified for a phone configuration using the phone configuration parameter: *contact* as noted above.

Multiple "contact" lines may be used for each phone configuration.

For XML configuration, Contacts files are specified using the *<contacts>* element.

Example URL: http://my.odoo.com:8069/phonebook/demo/digium_d/phonebook.xml


Fanvil
++++++
Go to *PHONE -> REMOTE CONTACT -> Remote Phonebook Settings*.

Add phonebook URL in the *Server URL field*. Example URL: http://my.odoo.com:8069/phonebook/demo/fanvil/phonebook.xml

Grandstream
+++++++++++
Grandseam phones add *phonebook.xml* to server URL. So You should specify only the part of URL.
Example: http://my.odoo.com:8069/phonebook/demo/gs/.

Panasonic
+++++++++
Set *Network -> Application Settings -> Enable Application [YES]*.

Set *Telephone -> Application Settings -> Network Phonebook URL* to 
http://my.odoo.com:8069/phonebook/demo/panasonic/contacts.xml.

Polycom
+++++++
As Polycom phones cannot get contact book from HTTP you need to create cron script that will
periodically download contacts from Odoo and put it in your TFTP server root where
your phones are provisoned.

Example:

.. code::

  curl -o 000000000000-directory.xml  http://my.odoo.com:8069/phonebook/demo/polycom/phonebook.xml

Refer to Polycom provision documentation for details or contact for support.

SNOM
++++
Add *phonebook* URL to <setting-files> tag. Example URL: http://my.odoo.com:8069/phonebook/demo/snom/phonebook.xml

According to documentation SNOM phones can store 100-250 directory entries. 
If you require some way to filter contacts that go to SNOM phones contact me for a discussion.


Yealink
+++++++
Specify yealink URL. Example: http://my.odoo.com:8069/phonebook/demo/yealink/phonebook.xml


Customization
-------------
You can easily customize phone templates.

Go to Settings -> Technical -> User Interface - Views.

Type phonebook in the search fields and press enter. You will see all templates of this module.

Find one that is required and customize it.


VoIP phones documentation
-------------------------
I have collected some links for your convinience. Please let me know if some links get broken.

* `Atcom <http://download.atcom.cn/phone/Guidedocument/ATCOM%20XML%20remote%20phonebook.pdf>`_
* `Audiocodes <https://www.audiocodes.com/media/13482/400hd-series-ip-phone-administrators-manual-ver-2216.pdf>`_
* `Grandstream <http://www.grandstream.com/sites/default/files/Resources/gxp_wp_xml_phonebook.pdf>`_
* `Panasonic <https://panasonic.net/cns/pcc/support/sipphone/download/TGP6/TGP600_HDV_XML_DevelopersGuide_Rev2.52.pdf>`_
* `Polycom <https://community.polycom.com/t5/VoIP-SIP-Phones/FAQ-How-can-I-create-a-local-directory-or-what-is-the/td-p/8216>`_
* `SNOM <http://wiki.snom.com/Features/Mass_Deployment/Setting_Files/XML/Directory>`_
* `Digium A series <https://wiki.asterisk.org/wiki/display/DIGIUM/A-Series+Contacts>`_
* `Digium D series <https://wiki.asterisk.org/wiki/display/DIGIUM/Contacts>`_

Changelog
---------
1.5
+++

* Added option to limit phonebook with selected only partners.

1.4
+++
* Addes option to strip formatting characters from phone numbers (in Settings).

1.3
+++
* Response header fix (returns text/xml instead of text/html).
* Settings page and HTTP auth option for phones models supporting this option.
* Aastra phones support added.
* Yealink phones support added.
* Atcom phones support added.
* Panasonic phones support added.
* Digium phones support added.
* Audiocodes phones support added.

1.2
+++
* SNOM phones support added.
* Fanvil phones support added.
* Odoo version 10.0 module release.

1.1
+++
* Polycom phones support added.


1.0
+++
* Initial release with Grandstream support.