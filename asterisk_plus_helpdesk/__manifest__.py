# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2021
# -*- encoding: utf-8 -*-
{
    'name': 'Asterisk Plus Helpdesk',
    'version': '1.0',
    'author': 'Odooist',
    'price': 250,
    'currency': 'EUR',
    'maintainer': 'Odooist',
    'support': 'odooist@gmail.com',
    'license': 'OPL-1',
    'category': 'Phone',
    'summary': 'Asterisk Plus Helpdesk integration',
    'description': "",
    'depends': ['helpdesk', 'asterisk_plus'],
    'data': [
        'security/server.xml',
        'views/ticket.xml',
        'views/call.xml',
    ],
    'demo': [],
    "qweb": ['static/src/xml/*.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
