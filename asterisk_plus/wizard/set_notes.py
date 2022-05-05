from odoo import models, fields


class AddNoteWizard(models.TransientModel):
    _name = 'asterisk_plus.set_notes_wizard'
    _description = 'Set note to call'

    notes = fields.Html()

    def set_notes(self):
        call = self.env['asterisk_plus.call'].browse(
            self.env.context['active_ids'])
        call.notes = self.notes
