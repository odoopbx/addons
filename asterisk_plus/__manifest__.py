# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
# -*- encoding: utf-8 -*-
{
    'name': 'Asterisk Plus',
    'version': '1.0',
    'author': 'Odooist',
    'price': 350,
    'currency': 'EUR',
    'maintainer': 'Odooist',
    'support': 'odooist@gmail.com',
    'license': 'LGPL-3',
    'category': 'Phone',
    'summary': 'Asterisk plus Odoo',
    'description': 'Asterisk plus Odoo',
    'depends': ['base', 'mail'],
    'external_dependencies': {
       'python': ['humanize', 'lameenc', 'phonenumbers', 'salt-pepper', 'SpeechRecognition', 'pyyaml'],
    },
    'data': [
        # Security rules
        'security/groups.xml',
        'security/server.xml',
        'security/server_record_rules.xml',
        'security/admin.xml',
        'security/admin_record_rules.xml',
        'security/user.xml',
        'security/user_record_rules.xml',
        'security/debug.xml',
        # Data
        'data/events.xml',
        'data/res_users.xml',
        'data/server.xml',
        # UI Views
        'views/menu.xml',
        'views/server.xml',
        'views/settings.xml',
        'views/about.xml',
        'views/event.xml',
        'views/recording.xml',
        'views/res_users.xml',
        'views/user.xml',
        'views/res_partner.xml',
        'views/call.xml',
        'views/channel.xml',
        'views/channel_message.xml',
        'views/templates.xml',
        'views/tag.xml',
        'views/conf.xml',
        'views/security.xml',
        # Cron
        'views/ir_cron.xml',
        # Wizards
        'wizard/set_notes.xml',
        'wizard/call.xml',
        # Reports
        'reports/reports.xml',
        'reports/calls_report.xml',
        # Web Phone
        'views/web_phone_user.xml',
        'views/web_phone_settings.xml',
    ],
    'demo': [],
    "qweb": [
        'static/src/xml/*.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/logo.png'],
    'assets': {
        'web.assets_backend': [
            '/asterisk_plus/static/src/js/support.js',
            '/asterisk_plus/static/src/js/actions.js',
            '/asterisk_plus/static/src/js/originate.js',
            '/asterisk_plus/static/src/js/web_phone.js',
            '/asterisk_plus/static/src/js/asterisk_conf.js',
            '/asterisk_plus/static/src/js/buttons.js',
            '/asterisk_plus/static/src/lib/jssip.min.js',
            '/asterisk_plus/static/src/scss/web_phone.scss',
            '/asterisk_plus/static/src/js/support_button.js',
        ],
        'web.assets_qweb': [
            'asterisk_plus/static/src/xml/**/*',
            'asterisk_plus/static/src/xml/web_phone.xml',
        ],
    }
}
