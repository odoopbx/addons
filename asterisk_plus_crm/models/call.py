# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2021
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.asterisk_plus.models.settings import debug

logger = logging.getLogger(__name__)


class CrmCall(models.Model):
    _inherit = 'asterisk_plus.call'

    ref = fields.Reference(selection_add=[('crm.lead', 'Leads')])

    def update_reference(self):
        res = super(CrmCall, self).update_reference()
        if not res:
            lead = None
            # No reference was set, so we have a change to set it to a lead
            debug(self, 'DIRECTION: {}'.format(self.direction))
            if self.direction == 'in':                
                lead = self.env['crm.lead'].get_lead_by_number(self.calling_number)
            else:
                lead = self.env['crm.lead'].get_lead_by_number(self.called_number)
            debug(self, 'LEAD: {}'.format(lead))
            if lead:
                self.ref = lead
                return True

    @api.constrains('is_active', 'direction')
    def auto_create_lead(self):
        auto_create_leads = self.env['asterisk_plus.settings'].get_param(
            'auto_create_leads_from_calls')
        if not auto_create_leads:
            return
        only_missed = self.env[
            'asterisk_plus.settings'].get_param(
            'auto_create_leads_for_missed_calls')
        only_for_unknown = self.env[
            'asterisk_plus.settings'].get_param(
            'auto_create_leads_for_unknown_callers')
        default_sales_person = self.env[
            'asterisk_plus.settings'].get_param(
            'auto_create_leads_sales_person')
        for rec in self:            
            if not self.direction == 'in' or rec.ref:
                # We only do it for incoming calls without reference.
                continue
            if not rec.is_active:
                # Call end
                if only_missed and rec.status != 'answered' and not rec.ref:
                    debug(self, 'CREATE LEAD FROM MISSED CALL')
                    lead = self.env['crm.lead'].create({
                        'name': rec.calling_name,
                        'type': 'lead',
                        'user_id': rec.called_user.id or default_sales_person.id,
                        'partner_id': rec.partner.id,
                        'phone': rec.calling_number,
                    })
                    rec.ref = lead
            else:
                # Call start
                lead = self.env['crm.lead'].get_lead_by_number(self.calling_number)
                if not lead:
                    # Create leads for all  incoming calls if no conditions set
                    if not any([only_missed, only_for_unknown]) or \
                            only_for_unknown and not rec.partner:
                        debug(self, 'CREATE LEAD FROM CALL START')
                        lead = self.env['crm.lead'].create({
                            'name': rec.calling_name,
                            'type': 'lead',
                            'user_id': rec.called_user.id or default_sales_person.id,
                            'partner_id': rec.partner.id,
                            'phone': rec.calling_number,
                        })
                        rec.ref = lead
                else:
                    # Lead found
                    rec.ref = lead


    def lead_button(self):
        self.ensure_one()
        context = {}
        if not self.ref:
            # Create a new lead
            self.ref = self.env['crm.lead'].with_context(
                call_id=self.id).create({'name': self.calling_name or self.calling_number})
            context['form_view_initial_mode'] = 'edit'
        # Open call lead
        if self.ref._name == 'crm.lead':
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'crm.lead',
                'res_id': self.ref.id,
                'name': 'Call Lead',
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'current',
                'context': context,
            }
        else:
            raise ValidationError(_('Reference already defined!'))