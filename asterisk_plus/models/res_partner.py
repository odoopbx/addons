# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import logging
import re
import phonenumbers
from phonenumbers import phonenumberutil
from odoo import models, fields, api, tools, _
from .settings import debug

logger = logging.getLogger(__name__)


def strip_number(number):
    """Strip number formating"""
    pattern = r'[\s()-]'
    return re.sub(pattern, '', number)


class Partner(models.Model):
    _inherit = ['res.partner']

    phone_normalized = fields.Char(compute='_get_phone_normalized',
                                   index=True, store=True,
                                   string='E.164 phone')
    mobile_normalized = fields.Char(compute='_get_phone_normalized',
                                    index=True, store=True,
                                    string='E.164 mobile')
    phone_extension = fields.Char(help=_(
        'Prefix with # to add 1 second pause before entering. '
        'Every # adds 1 second pause. Example: ###1001'))
    call_count = fields.Integer(compute='_get_call_count', string='Calls')
    recorded_calls = fields.One2many('asterisk_plus.recording', 'partner')

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
        except Exception as e:
            logger.exception(e)
        res = super(Partner, self).create(vals)
        if res and not self.env.context.get('no_clear_cache'):
            self.clear_caches()
        return res

    def write(self, values):
        res = super(Partner, self).write(values)
        if res and not self.env.context.get('no_clear_cache'):
            self.clear_caches()
        return res

    def unlink(self):
        res = super(Partner, self).unlink()
        if res and not self.env.context.get('no_clear_cache'):
            self.clear_caches()
        return res

    @api.model
    def originate_call(self, number, model=None, res_id=None, exten=None):
        """Originate Call to partner.

        Args:
            number (str): Number to dial.
            exten (str): Optional extension number to enter in DTMF mode after answer.
        """
        partner = self.browse(res_id)
        number = partner.phone_normalized
        extension = partner.phone_extension or ''
        # Minimum 1 second delay.
        dtmf_delay = extension.count('#') or 1
        # Now strip # and have only extension.
        dtmf_digits = extension.strip('#')
        self.env.user.asterisk_users[0].server.originate_call(
            number, model='model', res_id=res_id,
            dtmf_variables=['__dtmf_digits: {}'.format(dtmf_digits),
                            '__dtmf_delay: {}'.format(dtmf_delay)])

    @api.depends('phone', 'mobile', 'country_id')
    def _get_phone_normalized(self):
        for rec in self:
            rec.update({
                'phone_normalized': rec._normalize_phone(rec.phone) if rec.phone else False,
                'mobile_normalized': rec._normalize_phone(rec.mobile) if rec.mobile else False
            })

    def _normalize_phone(self, number):
        """Keep normalized phone numbers in normalized fields.
        """
        self.ensure_one()
        country_code = self._get_country_code()
        try:
            phone_nbr = phonenumbers.parse(number, country_code)
            if phonenumbers.is_possible_number(phone_nbr) or \
                    phonenumbers.is_valid_number(phone_nbr):
                number = phonenumbers.format_number(
                    phone_nbr, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.phonenumberutil.NumberParseException:
            pass
        except Exception as e:
            logger.warning('Normalize phone error: %s', e)
        # Strip the number if parse error.
        return number

    def search_by_number(self, number):
        """Search partner by number.
        Args:
            number (str): number to be searched on.
        If several partners are found by the same number:
        a) If partners belong to same company, return company record.
        b) If partners belong to different companies return False.
        """
        found = self.env['res.partner'].search([
            '|',
            ('phone_normalized', '=', number),
            ('mobile_normalized', '=', number)])
        debug(self, 'SEARCH_PARTNER_BY_NUMBER {} FOUND: {}'.format(number, found))
        parents = found.mapped('parent_id')
        # 1-st case: just one partner, perfect!
        if len(found) == 1:
            debug(self, 'FOUND PARTNER {} BY NUMBER {}'.format(found.name, number))
            return found[0]
        # 2-nd case: Many partners, no parent company / many companies
        elif len(parents) == 0 and len(found) > 1:
            logger.warning('MANY PARTNERS FOR NUMBER %s', number)
            debug(self, 'RETURN FIRST PARTNER FOR NUMBER {}'.format(number))
            return found[0]
        # 3-rd case: many partners, many companies
        elif len(parents) > 1 and len(found) > 1:
            logger.warning(
                'MANY PARTNERS DIFFERENT COMPANIES FOR NUMBER %s', number)
            return
        # 4-rd case: 1 partner from one company
        elif len(parents) == 1 and len(found) == 2 and len(
                found.filtered(
                    lambda r: r.parent_id.id in [k.id for k in parents])) == 1:
            debug(self, 'ONE PARTNER FROM ONE PARENT FOUND')
            return found.filtered(
                lambda r: r.parent_id in [k for k in parents])[0]
        # 5-rd case: many partners same parent company
        elif len(parents) == 1 and len(found) > 1 and len(found.filtered(
                lambda r: r.parent_id in [k for k in parents])) > 1:
            debug(self, 'MANY PARTNERS SAME PARENT COMPANY {}'.format(number))
            return parents[0]
        # 6-rd case: Nothing found
        else:
            debug(self, 'NO PARTNERS FOUND FOR NUMBER {}'.format(number))

    def search_by_caller_number(self, number):
        # Called from AMI events.fields.
        # Get country code of Asterisk server account 
        # or main company country if Asterisk account country is not set.
        return self.get_partner_by_number(number)['id']

    def _get_country_code(self):
        partner = self
        if partner and partner.country_id:
            # Return partner country code
            return partner.country_id.code
        elif partner and partner.parent_id and partner.parent_id.country_id:
            # Return partner's parent country code
            return partner.parent_id.country_id.code
        elif partner and partner.company_id and partner.company_id.country_id:
            # Return partner's company country code
            return partner.company_id.country_id.code
        elif self.env.user and self.env.user.company_id.country_id:
            # Return Odoo's main company country
            return self.env.user.company_id.country_id.code

    @api.model
    def _format_number(self, number, country_code=None, format_type='e164'):
        """Return number in requested format_type
        """
        debug(self, 'FORMAT_NUMBER {} COUNTRY {} FORMAT {}'.format(number, country_code, format_type))
        # Strip formatting if present
        number = strip_number(number)
        if len(self) == 1 and not country_code:
            # Called from partner object
            country_code = self._get_country_code()
            debug(self, 'GOT COUNTRY FOR PARTNER {} CODE {}'.format(self, country_code))
        elif not country_code:
            # Get country code for requesting account
            country_code = self.env.user.partner_id._get_country_code()
            debug(self, 'GOT COUNTRY CODE {} FROM ENV USER'.format(country_code))
        if country_code is False:
            # False -> None
            country_code = None
        try:
            phone_nbr = phonenumbers.parse(number, country_code)
            if not phonenumbers.is_possible_number(phone_nbr):
                debug(self, 'PHONE NUMBER {} NOT POSSIBLE'.format(number))
            elif not phonenumbers.is_valid_number(phone_nbr):
                debug(self, 'PHONE NUMBER {} NOT VALID'.format(number))
            # We have a parsed number, let check what format to return.
            elif format_type == 'out_of_country':
                # For out of country format we must get the Asterisk
                # agent country to format numbers according to it.
                country_code = self.env.user.partner_id._get_country_code()
                number = phonenumbers.format_out_of_country_calling_number(
                    phone_nbr, country_code)
                debug(self, 'OUT OF COUNTRY FORMATTED NUMBER: {}'.format(number))
            elif format_type == 'e164':
                number = phonenumbers.format_number(
                    phone_nbr, phonenumbers.PhoneNumberFormat.E164)
                debug(self, 'E164 FORMATTED NUMBER: {}'.format(number))
            elif format_type == 'international':
                number = phonenumbers.format_number(
                    phone_nbr, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                debug(self, 'INTERN FORMATTED NUMBER: {}'.format(number))
            else:
                logger.error('WRONG FORMATTING PASSED: %s', format_type)
        except phonenumberutil.NumberParseException:
            debug(self, 'PHONE NUMBER {} PARSE ERROR'.format(number))
        except Exception:
            logger.exception('FORMAT NUMBER ERROR:')
        finally:
            return number

    @api.model
    @tools.ormcache('number', 'country_code')
    def get_partner_by_number(self, number, country_code=None):
        # Default values
        partner_info = {'name': _('Unknown'), 'id': False}
        debug(self, 'GET_PARTNER_BY_NUMBER {} COUNTRY {}'.format(number, country_code))
        if not number:
            debug(self, 'NO NUMBER PASSED')
            return partner_info
        if 'unknown' in number or number == 's':
            debug(self, '<UNKNOWN>/s NUMBER PASSED')
            return partner_info
        partner = None
        # 1. Convert to E.164 and make a search
        e164_number = self._format_number(
            number, country_code=country_code, format_type='e164')
        partner = self.search_by_number(e164_number)
        # 2. Make a search as as.
        if not partner:
            partner = self.search_by_number(number)
        # 3. Add + and make a search.
        if not partner:
            number_plus = '+' + number if number[0] != '+' else number
            partner = self.search_by_number(number_plus)
        if partner:
            # We have partner, populate result data.
            partner_info['id'] = partner.id
            if partner.parent_name:
                partner_info['name'] = u'{} ({})'.format(partner.name,
                                                         partner.parent_name)
            else:
                partner_info['name'] = partner.name
                # On Odoo 10 we have to use unicode formatting!
                debug(self, u'FOUND PARTNER {}'.format(partner_info['name']))
        else:
            debug(self, 'NO PARTNER FOUND')
        return partner_info

    def _get_call_count(self):
        for rec in self:
            if rec.is_company:
                rec.call_count = self.env[
                    'asterisk_plus.call'].sudo().search_count(
                    ['|', ('partner', '=', rec.id),
                          ('partner.parent_id', '=', rec.id)])
            else:
                rec.call_count = self.env[
                    'asterisk_plus.call'].sudo().search_count(
                    [('partner', '=', rec.id)])
