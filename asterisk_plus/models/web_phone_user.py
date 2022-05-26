# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from .settings import debug

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
                self.env['asterisk_plus.user'].generate_configs()
        return res

    def unlink(self):
        res = super(WebPhoneUser, self).unlink()
        self.env['asterisk_plus.user'].generate_configs()
        return res

    def _compute_sip_autocreate_enabled(self):
        for rec in self:
            rec.is_sip_autocreate_enabled = self.env[
                'asterisk_plus.settings'].sudo().get_param('auto_create_sip_peers')

