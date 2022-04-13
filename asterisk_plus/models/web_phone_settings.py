# -*- coding: utf-8 -*-
from odoo import fields, models

WEB_PHONE_SIP_TEMPLATE="""[{0}](odoo-user)
inbound_auth/username = {0}
inbound_auth/password = {1}
"""

class WebPhoneSettings(models.Model):
    _inherit = 'asterisk_plus.settings'

    web_phone_sip_protocol = fields.Char(string="SIP Protocol", default='udp')
    web_phone_sip_proxy = fields.Char(string="SIP Proxy")
    web_phone_websocket = fields.Char(string="Websocket")
    web_phone_stun_server = fields.Char(string="Stun Server", default='stun.l.google.com:19302')
    is_web_phone_enabled = fields.Boolean(string="Enabled", default=True)
    web_phone_sip_template = fields.Text(
        string="SIP Template",
        help="SIP configuration template for new users",
        default=WEB_PHONE_SIP_TEMPLATE)
