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
