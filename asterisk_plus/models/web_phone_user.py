# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from .settings import debug
from odoo.addons import base

logger = logging.getLogger(__name__)

WEB_PHONE_USER_FIELDS = ['web_phone_sip_user', 'web_phone_sip_secret']

class WebPhoneUser(models.Model):
    _inherit = 'res.users'

    web_phone_sip_user = fields.Char(string="SIP User")
    web_phone_sip_secret = fields.Char(string="SIP Secret")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + WEB_PHONE_USER_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + WEB_PHONE_USER_FIELDS