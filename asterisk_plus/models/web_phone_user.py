# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from passlib import pwd
from random import choice
from .settings import debug
from .web_phone_settings import WEB_PHONE_SIP_CONFIG
from .server import get_default_server

logger = logging.getLogger(__name__)


class WebPhoneUser(models.Model):
    _inherit = 'res.users'
    _description = "Web Phone"

    web_phone_sip_user = fields.Char(string="SIP User")
    web_phone_sip_secret = fields.Char(string="SIP Secret")

    @api.model
    def create(self, values):
        def get_next_exten(elements):
            res = set()
            for element in elements:
                try:
                    res.add(int(element))
                except ValueError:
                    #ignore non-numeric values
                    continue
            if res:
                return max(res)+1
            else:
                return 101

        user = super(WebPhoneUser, self).create(values)

        if not self.env['asterisk_plus.settings'].sudo().get_param('auto_create_sip_peers'):
            return user
        # create sip peer for internal users only
        if not user.has_group('base.group_user'):
            return user
        # create new user
        debug(self,"Creating new user {}".format(values.get('name')))
        values['web_phone_sip_user'] = values.get('login')
        values['web_phone_sip_secret'] = pwd.genword(length=choice(range(12,16)))
        # choose new exten
        new_exten = get_next_exten([
            k.exten for k in self.env['asterisk_plus.user'].search([])
        ])

        # create new asterisk_user
        asterisk_user = self.env['asterisk_plus.user'].create([{'exten': new_exten, 'user': user.id}])

        # create user channel
        user_channel = self.env['asterisk_plus.user_channel'].create({
            'name': f'PJSIP/{user.web_phone_sip_user}',
            'asterisk_user': asterisk_user.id
        })

        self.update_webphone_sip_config()

        return user

    def write(self, vals):
        res = super(WebPhoneUser, self).write(vals)
        if not self.env['asterisk_plus.settings'].sudo().get_param('auto_create_sip_peers'):
            return res
        if 'web_phone_sip_user' in vals or 'web_phone_sip_secret' in vals:
            self.pool.clear_caches()
            self.update_webphone_sip_config()
        return res

    @api.model
    def update_webphone_sip_config(self):
        # update or create configuration file for web phone users
        default_server = get_default_server(self)
        config = self.env['asterisk_plus.conf'].get_or_create(default_server.id, WEB_PHONE_SIP_CONFIG)
        template = self.env['asterisk_plus.settings'].sudo().get_param('web_phone_sip_template')
        content = ""

        for user in self.search([]):
            name, secret = user['web_phone_sip_user'], user['web_phone_sip_secret']
            if name and secret:
                content += template.format(name, secret)+"\n"

        config.write({'content': content})

        return
