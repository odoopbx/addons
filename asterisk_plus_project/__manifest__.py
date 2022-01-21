# -*- encoding: utf-8 -*-
{
    'name': 'Asterisk Plus Project',
    'version': '1.0',
    'author': 'Odooist',
    'price': 0,
    'currency': 'EUR',
    'maintainer': 'Odooist',
    'support': 'odooist@gmail.com',
    'license': 'LGPL-3',
    'category': 'Phone',
    'summary': 'Asterisk Plus Project integration',
    'description': "",
    'depends': ['project', 'asterisk_plus'],
    'data': [
        'views/project.xml',
        'views/task.xml',
        'views/call.xml',
        'security/server.xml',
    ],
    'demo': [],
    "qweb": ['static/src/xml/*.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/logo.png'],
}
