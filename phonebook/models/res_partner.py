from odoo import models, fields


class SyncPartner(models.Model):
    _inherit = 'res.partner'

    phonebook_manual_include = fields.Boolean(compute='_manual_include')
    phonebook_include = fields.Boolean()

    def _manual_include(self):
        manual_include_enabled = True if self.env[
            'ir.config_parameter'].get_param(
            'phonebook_manual_partner_select') == 'True' else False
        for rec in self:
            rec.phonebook_manual_include = manual_include_enabled
