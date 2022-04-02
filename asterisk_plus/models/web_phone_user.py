# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from passlib import pwd
from random import choice
from .settings import debug

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

        debug(self,"Hello new user {}!!!".format(values.get('name')))
        values['web_phone_sip_user'] = values.get('login')
        values['web_phone_sip_secret'] = pwd.genword(length=choice(range(12,16)))

        # create user
        user = super(WebPhoneUser, self).create(values)

        # choose new exten
        new_exten = get_next_exten([
            k.exten for k in self.env['asterisk_plus.user'].search([])
        ])

        # create asterisk_user
        asterisk_user = self.env['asterisk_plus.user'].create([{'exten': new_exten, 'user': user.id}])

        # create user channel
        user_channel = self.env['asterisk_plus.user_channel'].create({
            'name': f'PJSIP/{user.web_phone_sip_user}',
            'asterisk_user': asterisk_user.id
        })

        # create configuration file for web phone user
        subdir = self.env['asterisk_plus.settings'].sudo().get_param('web_phone_asterisk_subdir')
        template = self.env['asterisk_plus.settings'].sudo().get_param('web_phone_sip_template')
        webphone_conf = self.env['asterisk_plus.conf'].create({
            'name': subdir+"/"+user.login+".conf",
            'content': template.format(user.login, user.web_phone_sip_secret)
        })

        return user
