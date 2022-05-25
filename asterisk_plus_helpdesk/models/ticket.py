# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2021
import logging
from odoo import api, models, fields, _

logger = logging.getLogger(__name__)


class Ticket(models.Model):
    _name = 'helpdesk.ticket'
    _inherit = 'helpdesk.ticket'

    asterisk_calls_count = fields.Integer(compute='_get_asterisk_calls_count',
                                          string=_('Calls'))
    partner_phone = fields.Char(related='partner_id.phone')
    partner_mobile = fields.Char(related='partner_id.mobile')

    def _get_asterisk_calls_count(self):
        for rec in self:
            rec.asterisk_calls_count = self.env[
                'asterisk_plus.call'].search_count([
                    ('res_id', '=', rec.id),
                    ('model', '=', 'helpdesk.ticket')])

    @api.model
    def create(self, vals):
        try:
            if self.env.context.get('call_id'):
                call = self.env['asterisk_plus.call'].browse(
                    self.env.context['call_id'])
                if call.partner:
                    vals['partner_id'] = call.partner.id
        except Exception as e:
            logger.exception(e)
        res = super(Ticket, self).create(vals)
        if res:
            self.pool.clear_caches()
        return res
