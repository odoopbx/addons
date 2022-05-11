from odoo import models, fields, api, _


class Debug(models.Model):
    _name = 'asterisk_plus.debug'
    _description = 'Asterisk Debug'
    _order = 'id desc'
    _rec_name = 'id'

    model = fields.Char()
    message = fields.Text()
