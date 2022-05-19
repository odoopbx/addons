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
    is_sip_autocreate_enabled = fields.Char(compute='_compute_sip_autocreate_enabled')

    @api.model
    def create(self, values):
        user = super(WebPhoneUser, self).create(values)
        debug(self, f"Created user {user.login}")
        # create SIP account if enabled
        if self.env['asterisk_plus.settings'].sudo().get_param('auto_create_sip_peers'):
            self.env['asterisk_plus.user'].auto_create(user)
        return user

    def write(self, vals):
        debug(self, f"Updating user {self.login} web_phone settings")
        res = super(WebPhoneUser, self).write(vals)
        if 'web_phone_sip_user' in vals or 'web_phone_sip_secret' in vals:
            if not self.env.context.get('skip_update_config'):
                self.update_webphone_sip_config()
        return res

    def unlink(self):
        res = super(WebPhoneUser, self).unlink()
        self.update_webphone_sip_config()
        return res

    def _compute_sip_autocreate_enabled(self):
        for rec in self:
            if self.env['asterisk_plus.settings'].sudo().get_param('auto_create_sip_peers'):
                rec.is_sip_autocreate_enabled = True
            else:
                rec.is_sip_autocreate_enabled = False

    @api.model
    def update_webphone_sip_config(self):
        """Generate asterisk SIP configuration file for web_phone users
        """
        default_server = get_default_server(self)
        config = self.env['asterisk_plus.conf'].get_or_create(default_server.id, WEB_PHONE_SIP_CONFIG)
        template = self.env['asterisk_plus.settings'].sudo().get_param('web_phone_sip_template')
        content = ""

        for user in self.search([('web_phone_sip_user', '!=', ''),('web_phone_sip_secret', '!=', '')]):
            content += template.format(user.web_phone_sip_user, user.web_phone_sip_secret )+"\n"

        if config.content != content:
            config.write({'content': content})
            debug(self, f"Updated {WEB_PHONE_SIP_CONFIG} config")

        return
