import logging
from odoo import api, fields, models, _, SUPERUSER_ID

logger = logging.getLogger(__name__)


class PhonebookSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    PHONEBOOK_PARAMS = [
        ('phonebook_gs_auth_enabled', 'False'),
        ('phonebook_auth_basic_username', ''),
        ('phonebook_auth_basic_password', ''),
        ('phonebook_ip_acl', '0.0.0.0/0'),
        ('phonebook_strip_plus', 'False'),
        ('phonebook_add_plus', 'False'),
        ('phonebook_strip_formatting', 'False'),
        ('phonebook_manual_partner_select', 'False'),
    ]

    phonebook_gs_auth_enabled = fields.Boolean(
        string=_('Grandsream HTTP auth'))
    phonebook_auth_basic_username = fields.Char(string=_('HTTP username'))
    phonebook_auth_basic_password = fields.Char(string=_('HTTP password'))
    phonebook_ip_acl = fields.Char(string=_('IP ACL'))
    phonebook_strip_plus = fields.Boolean(string='Strip Plus')
    phonebook_add_plus = fields.Boolean(string='Add Plus')
    phonebook_strip_formatting = fields.Boolean(string='Strip Formatting')
    phonebook_manual_partner_select = fields.Boolean(
        string='Manually Select Partners')

    def set_values(self):
        super(PhonebookSettings, self).set_values()
        for field_name, default_value in self.PHONEBOOK_PARAMS:
            value = getattr(self, field_name) or default_value
            self.env['ir.config_parameter'].set_param(field_name, str(value))

    @api.model
    def get_default_values(self, fields):
        return self.get_values()

    @api.model
    def get_values(self):
        res = super(PhonebookSettings, self).get_values()
        for field_name, default_value in self.PHONEBOOK_PARAMS:
            res[field_name] = self.env[
                'ir.config_parameter'].get_param(field_name, default_value)
            # Convert bool values
            if field_name in ['phonebook_gs_auth_enabled',
                              'phonebook_strip_plus', 'phonebook_add_plus',
                              'phonebook_manual_partner_select',
                              'phonebook_strip_formatting']:
                res[field_name] = True if res[field_name] == 'True' else False
        return res
