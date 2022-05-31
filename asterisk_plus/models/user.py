import logging
from odoo import models, fields, api, tools, release, _
from odoo.exceptions import ValidationError, UserError
from .server import get_default_server
from .settings import debug
from passlib import pwd
from random import choice
from .web_phone_settings import WEB_PHONE_SIP_CONFIG, EXTENSIONS_CONFIG

logger = logging.getLogger(__name__)


class PbxUser(models.Model):
    _name = 'asterisk_plus.user'
    _inherit = 'mail.thread'
    _description = _('Asterisk User')

    exten = fields.Char()
    user = fields.Many2one('res.users', required=True,
                           ondelete='cascade',
                           # Exclude shared users
                           domain=[('share', '=', False)])
    name = fields.Char(related='user.name', readonly=True)
    #: Server where the channel is defined.
    server = fields.Many2one('asterisk_plus.server', required=True,
                             ondelete='restrict', default=get_default_server)
    server_id = fields.Char(related='server.server_id')
    channels = fields.One2many('asterisk_plus.user_channel',
                               inverse_name='asterisk_user')
    originate_vars = fields.Text(string='Channel Variables')
    open_reference = fields.Boolean(
        default=True,
        help=_('Open reference form on incoming calls.'))
    user_call_count = fields.Integer(compute='_get_call_count', string='Calls')
    missed_calls_notify = fields.Boolean(
        default=True,
        help=_('Notify user on missed calls.'))
    call_popup_is_enabled = fields.Boolean(
        default=True,
        string='Call Popup')
    call_popup_is_sticky = fields.Boolean(
        default=False,
        string='Popup Is Sticky')

    _sql_constraints = [
        ('exten_uniq', 'unique (exten,server)',
         _('This phone extension is already used!')),
        ('user_uniq', 'unique ("user",server)',
         _('This user is already defined!')),
    ]

    @api.model
    def create(self, vals):
        user = super(PbxUser, self).create(vals)
        if user and not self.env.context.get('no_clear_cache'):
            self.pool.clear_caches()
        if hasattr(self, 'generate_configs') and not self.env.context.get('skip_update_config'):
            self.generate_configs()
        return user

    def write(self, vals):
        user = super(PbxUser, self).write(vals)
        if user and not self.env.context.get('no_clear_cache'):
            self.pool.clear_caches()
        if 'exten' or 'user' in vals:
            if hasattr(self, 'generate_configs') and not self.env.context.get('skip_update_config'):
                self.generate_configs()
        return user

    def unlink(self):
        res = super().unlink()
        self.generate_configs()
        return res


    @api.model
    def auto_create(self, users):
        """Auto create pbx user for every record in "users" recordset
        """
        extensions = {int(el) for el in self.search([]).mapped('exten') if el.isdigit()}
        if extensions:
            next_extension = max(extensions) + 1
        else:
            next_extension = 101

        for user in users:
            # create SIP account only for internal users
            if not user.has_group('base.group_user'):
                continue

            # create new pbx user
            debug(self, f"Creating pbx user {user.login} with extension {next_extension}")
            asterisk_user = self.with_context(skip_update_config=True).create([
                {'exten': f"{next_extension}", 'user': user.id},
            ])

            # create new channel for newly created user
            user_channel = self.env['asterisk_plus.user_channel'].create({
                'name': 'PJSIP/' + user.login,
                'asterisk_user': asterisk_user.id
            })

            # create SIP user and secret for odoo user account
            user.with_context(skip_update_config=True).write({
                'web_phone_sip_user':  user.login,
                'web_phone_sip_secret': pwd.genword(length=choice(range(12,16)))
            })

            next_extension += 1

        self.generate_configs()

    @api.model
    def generate_configs(self):
        """Generate asterisk SIP and extensions configuration file for odoo users
        """
        default_server = get_default_server(self)
        extensions_config = self.env['asterisk_plus.conf'].get_or_create(
            default_server.id, EXTENSIONS_CONFIG)
        sip_config = self.env['asterisk_plus.conf'].get_or_create(
            default_server.id, WEB_PHONE_SIP_CONFIG)
        sip_template = self.env['asterisk_plus.settings'].sudo().get_param('web_phone_sip_template')
        sip_content = ";AUTOGENERATED BY ODOO\n"
        extensions_content = ";AUTOGENERATED BY ODOO\n[odoo-hints]\n"

        for user in self.search([]):
            sip_content += sip_template.format(user.user.web_phone_sip_user, user.user.web_phone_sip_secret ) + "\n"
            extensions_content += f"exten => {user.exten},hint,PJSIP/{user.user.web_phone_sip_user}\n"

        if sip_config.content != sip_content:
            sip_config.write({'content': sip_content})
            debug(self, f"Updated {WEB_PHONE_SIP_CONFIG}")
        if extensions_config.content != extensions_content:
            extensions_config.write({'content': extensions_content})
            debug(self, f"Updated {EXTENSIONS_CONFIG}")
        default_server.apply_changes()
        return

    @api.model
    def has_asterisk_plus_group(self):
        """Used from actions.js to check if Odoo user is enabled to
        use Asterisk applications in order to start a bus listener.
        """
        if (self.env.user.has_group('asterisk_plus.group_asterisk_admin') or
                self.env.user.has_group(
                    'asterisk_plus.group_asterisk_user')):
            return True

    def _get_originate_vars(self):
        self.ensure_one()
        try:
            if not self.originate_vars:
                return []
            return [k for k in self.originate_vars.split('\n') if k]
        except Exception:
            logger.exception('Get originate vars error:')
            return []

    def dial_user(self):
        self.ensure_one()
        self.env.user.asterisk_users[0].server.originate_call(
            self.exten, model='asterisk_plus.user', res_id=self.id)

    def open_user_form(self):
        if self.env.user.has_group('asterisk_plus.group_asterisk_admin'):
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'asterisk_plus.user',
                'name': 'Users',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'target': 'current',
            }
        else:
            if not self.env.user.asterisk_users:
                raise ValidationError('PBX user is not configured!')
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'asterisk_plus.user',
                'res_id': self.env.user.asterisk_users.id,
                'name': 'User',
                'view_id': self.env.ref(
                    'asterisk_plus.asterisk_plus_user_user_form').id,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'current',
            }

    @api.model
    @tools.ormcache('exten', 'system_name')
    def get_res_user_id_by_exten(self, exten, system_name):
        # TODO: Is it required?
        astuser = self.search([
            ('exten', '=', exten), ('system_name', '=', system_name)], limit=1)
        debug(self, 'GET RES USER BY EXTEN {} at {}: {}'.format(
            exten, system_name, astuser))
        return astuser.user.id

    def _get_call_count(self):
        for rec in self:
            rec.user_call_count = self.env[
                'asterisk_plus.call'].sudo().search_count(
                ['|', ('calling_user', '=', rec.user.id),
                      ('called_user', '=', rec.user.id)])

    def action_view_calls(self):
        # Used from the user calls view button.
        self.ensure_one()
        return {
            'name': _("Calls"),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'asterisk_plus.call',
            'domain': ['|', ('calling_user', '=', self.user.id),
                            ('called_user', '=', self.user.id)],
        }
