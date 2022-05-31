# -*- coding: utf-8 -*-
from odoo import fields, models, api
from .settings import debug

EXTENSIONS_CONFIG="odoo_hints.conf"
WEB_PHONE_SIP_CONFIG="odoo_pjsip_users.conf"
WEB_PHONE_SIP_TEMPLATE="""[{0}](odoo-webrtc-cuser)
inbound_auth/username = {0}
inbound_auth/password = {1}
"""

class WebPhoneSettings(models.Model):
    _inherit = 'asterisk_plus.settings'

    web_phone_sip_protocol = fields.Char(string="SIP Protocol", default="wss")
    web_phone_sip_proxy = fields.Char(string="SIP Proxy")
    web_phone_websocket = fields.Char(string="Websocket")
    web_phone_stun_server = fields.Char(string="Stun Server", default='stun.l.google.com:19302')
    is_web_phone_enabled = fields.Boolean(string="Enabled", default=True)
    auto_create_sip_peers = fields.Boolean(string="Autocreate peers",
        help="""Automatically generate SIP peers and extensions for Odoo users.
                Autogenerates %s and %s""" % (WEB_PHONE_SIP_CONFIG, EXTENSIONS_CONFIG))
    web_phone_sip_template = fields.Text(
        string="SIP Template",
        help="SIP configuration template for new users",
        default=WEB_PHONE_SIP_TEMPLATE)

    @api.model
    def run_auto_create_sip_peers(self):
        if hasattr(self.env['asterisk_plus.user'], 'auto_create'):
            debug(self, 'Enabling auto create SIP peers.')
            users = self.env['res.users'].search([])
            pbx_users = self.env['asterisk_plus.user'].search([]).mapped('user')
            self.env['asterisk_plus.user'].auto_create(users-pbx_users)
