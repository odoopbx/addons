# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2021
from odoo import models, fields


class HelpdeskCall(models.Model):
    _name = 'asterisk_plus.call'
    _inherit = 'asterisk_plus.call'

    ref = fields.Reference(selection_add=[
        ('helpdesk.ticket', 'Tickets')])

    def update_reference(self):
        res = super(HelpdeskCall, self).update_reference()
        if not res:
            if self.partner:
                ticket = self.env['helpdesk.ticket'].search([
                    ('partner_id', '=', self.partner.id)], limit=1)
                if ticket:
                    self.ref = ticket
                    return True
