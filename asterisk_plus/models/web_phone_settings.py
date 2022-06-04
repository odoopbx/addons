# -*- coding: utf-8 -*-
from odoo import fields, models, api
from .settings import debug

class WebPhoneSettings(models.Model):
    _inherit = 'asterisk_plus.settings'

    web_phone_sip_protocol = fields.Char(string="SIP Protocol", default="wss")
    web_phone_sip_proxy = fields.Char(string="SIP Proxy")
    web_phone_websocket = fields.Char(string="Websocket")
    web_phone_stun_server = fields.Char(string="Stun Server", default='stun.l.google.com:19302')
    is_web_phone_enabled = fields.Boolean(string="Enabled", default=True)
