# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import logging
from phonenumbers import phonenumberutil
import phonenumbers
from odoo import api, models, tools, fields, release, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.asterisk_plus.models.settings import debug
from odoo.addons.asterisk_plus.models.res_partner import strip_number

logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = 'crm.lead'

    asterisk_calls_count = fields.Integer(compute='_get_asterisk_calls_count',
                                          string=_('Calls'))
    phone_normalized = fields.Char(compute='_get_phone_normalized',
                                   index=True, store=True)
    mobile_normalized = fields.Char(compute='_get_phone_normalized',
                                    index=True, store=True)

    def write(self, values):
        res = super(Lead, self).write(values)
        if res:
            self.pool.clear_caches()
        return res

    def unlink(self):
        res = super(Lead, self).unlink()
        if res:
            self.pool.clear_caches()
        return res

    @api.model
    def create(self, vals):        
        try:
            if self.env.context.get('call_id'):
                call = self.env['asterisk_plus.call'].browse(
                    self.env.context['call_id'])
                if call.direction == 'in':
                    vals['phone'] = call.calling_number
                else:
                    vals['phone'] = call.called_number
                if call.partner:
                    vals['partner_id'] = call.partner.id
        except Exception as e:
            logger.exception(e)
        res = super(Lead, self).create(vals)
        if res:
            self.pool.clear_caches()
        return res

    @api.depends('phone', 'mobile', 'country_id', 'partner_id', 'partner_id.phone', 'partner_id.mobile')
    def _get_phone_normalized(self):
        for rec in self:            
            if release.version_info[0] >= 14:
                # Odoo > 14.0
                if rec.phone:
                    rec.phone_normalized = rec.normalize_phone(rec.phone)
                if rec.mobile:
                    rec.mobile_normalized = rec.normalize_phone(rec.mobile)
            else:
                # Old Odoo versions
                if rec.partner_id:
                    # We have partner set, take phones from him.
                    if rec.partner_id.phone:
                        rec.phone_normalized = rec.normalize_phone(
                            rec.partner_id.phone)
                    if rec.partner_id.mobile:
                        rec.mobile_normalized = rec.normalize_phone(rec.partner_id.mobile)
                else:
                    # No partner set takes phones from lead.
                    if rec.phone:
                        rec.phone_normalized = rec.normalize_phone(rec.phone)
                    if rec.mobile:
                        rec.mobile_normalized = rec.normalize_phone(rec.mobile)

    def _get_country_code(self):
        if self and self.country_id:
            return self.country_id.code
        elif self and self.partner_id and self.partner_id.country_id:
            return self.partner_id._get_country_code()
        else:
            if self.env.user and self.env.user.company_id.country_id:
                # Return Odoo's main company country
                return self.env.user.company_id.country_id.code

    def normalize_phone(self, number):
        self.ensure_one()
        number = strip_number(number)
        country_code = self._get_country_code()
        try:
            phone_nbr = phonenumbers.parse(number, country_code)
            if phonenumbers.is_possible_number(phone_nbr):
                number = phonenumbers.format_number(
                    phone_nbr, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.phonenumberutil.NumberParseException:
            pass
        except Exception as e:
            logger.warning('Normalize phone error: %s', e)
        # Strip the number if no phone validation installed or parse error.
        return number

    def _get_asterisk_calls_count(self):
        for rec in self:
            rec.asterisk_calls_count = self.env[
                'asterisk_plus.call'].search_count(
                    [('res_id', '=', rec.id), ('model', '=', 'crm.lead')])

    def _search_lead_by_number(self, number):
        # Odoo < 12 does not have partner_address_phone field.
        domain = [
            ('active', '=', True),
            '|',
            ('phone_normalized', '=', number),
            ('mobile_normalized', '=', number)]
        # Get last open lead
        found = self.env['crm.lead'].search(domain, order='id desc')
        if len(found) == 1:
            debug(self, 'FOUND LEAD {} BY NUMBER {}'.format(found[0].id, number))
            return found[0]
        elif len(found) > 1:
            logger.warning('[ASTCALLS] MULTIPLE LEADS FOUND BY NUMBER %s', number)
            return found[0]
        else:
            debug(self, 'LEAD BY NUMBER {} NOT FOUND'.format(number))

    @tools.ormcache('number', 'country_code')
    def get_lead_by_number(self, number, country_code=None):
        if not number or 'unknown' in number or number == 's':
            debug(self, 'GET LEAD BY NUMBER NO NUMBER PASSED')
            return
        lead = None
        # 1. Convert to E.164 and make a search
        e164_number = self._format_number(
            number, country_code=country_code, format_type='e164')
        lead = self._search_lead_by_number(e164_number)
        # 2. Make a search as as.
        if not lead:
            lead = self._search_lead_by_number(number)
        # 3. Add + and make a search.
        if not lead:
            number_plus = '+' + number if number[0] != '+' else number
            lead = self._search_lead_by_number(number_plus)
        debug(self, 'GET LEAD BY NUMBER RESULT: {}'.format(
            lead.id if lead else None))
        return lead

    def _format_number(self, number, country_code=None, format_type='e164'):
        # Strip formatting if present
        number = number.replace(' ', '')
        number = number.replace('(', '')
        number = number.replace(')', '')
        number = number.replace('-', '')
        if len(self) == 1 and not country_code:
            # Called from partner object
            country_code = self._get_country_code()
            logger.debug(
                'COUNTRY FOR LEAD %s CODE %s', self, country_code)
        elif not country_code:
            # Get country code for requesting account
            country_code = self.env.user.partner_id._get_country_code()
            logger.debug(self, 'LEAD GOT COUNTRY CODE %s FROM ENV USER', country_code)
        elif not country_code:
            logger.debug(self, 'LEAD COULD NOT GET COUNTRY CODE')
        if country_code is False:
            # False -> None
            country_code = None
        try:
            phone_nbr = phonenumbers.parse(number, country_code)
            if not phonenumbers.is_possible_number(phone_nbr):
                logger.debug(self, 'LEAD PHONE NUMBER {} NOT POSSIBLE'.format(number))
            elif not phonenumbers.is_valid_number(phone_nbr):
                logger.debug(self, 'LEAD PHONE NUMBER {} NOT VALID'.format(number))
            elif format_type == 'e164':
                number = phonenumbers.format_number(
                    phone_nbr, phonenumbers.PhoneNumberFormat.E164)
                logger.debug(self, 'LEAD E164 FORMATTED NUMBER: {}'.format(number))
            else:
                logger.error('LEAD WRONG FORMATTING PASSED: %s', format_type)
        except phonenumberutil.NumberParseException:
            logger.debug(self, 'LEAD PHONE NUMBER {} PARSE ERROR'.format(number))
        except Exception:
            logger.exception('LEAD FORMAT NUMBER ERROR:')
        finally:
            return number
