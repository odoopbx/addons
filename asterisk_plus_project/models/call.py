import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)


class ProjectCall(models.Model):
    _name = 'asterisk_plus.call'
    _inherit = 'asterisk_plus.call'

    ref = fields.Reference(selection_add=[
        ('project.task', 'Tasks'),
        ('project.project', 'Projects')])

    def update_reference(self):
        res = super(ProjectCall, self).update_reference()
        if not res:
            # No reference was set, so we have a change to set it to a task or project
            if self.partner:
                task = self.env['project.task'].search([
                    ('partner_id', '=', self.partner.id)], limit=1)
                project = self.env['project.project'].search([
                    ('partner_id', '=', self.partner.id)], limit=1)
                if task:
                    self.ref = task
                    return True
                elif project:
                    self.ref = project
                    return True

    def task_button(self):
        self.ensure_one()
        context = {}
        if not self.ref:
            # Create a new task
            self.ref = self.env['project.task'].with_context(
                call_id=self.id).create({'name': self.calling_name or self.calling_number})
            context['form_view_initial_mode'] = 'edit'
        # Open call lead
        if self.ref._name == 'project.task':
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'project.task',
                'res_id': self.ref.id,
                'name': 'Call Lead',
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'current',
                'context': context,
            }
        else:
            raise ValidationError(_('Reference already defined!'))
