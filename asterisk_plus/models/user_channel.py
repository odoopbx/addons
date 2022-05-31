# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
from datetime import datetime, timedelta
import json
import logging
from odoo import models, fields, api, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
from .server import debug

logger = logging.getLogger(__name__)

#: Fields allowed to be changed by user.
USER_PERMITTED_FIELDS = [
    'originate_vars', 'channels', 'originate_enabled', 'auto_answer_header',
]

#: When click to dial is used to originate call to a partner Asterisk first makes
#: a call to user (1-st call leg) and after user answered his phone the 2-nd call leg
#: is originated to the partner number. It is possible to auto answer the 1-st leg using
#: special channel headers. Different phones use different headers.
#: https://docs.odoopbx.com/user_guide/auto_answer.html
AUTO_ANSWER_HEADERS = [
    ('Alert-Info: Info=Alert-Autoanswer', 'Alert-Info: Info=Alert-Autoanswer'),
    ('Alert-Info: Info=Auto Answer', 'Alert-Info: Info=Auto Answer'),
    ('Alert-Info: ;info=alert-autoanswer', 'Alert-Info: ;info=alert-autoanswer'),
    ('Alert-Info: <sip:>;info=alert-autoanswer', 'Alert-Info: <sip:>;info=alert-autoanswer'),
    ('Alert-Info: Ring Answer', 'Alert-Info: Ring Answer'),
    ('Answer-Mode: Auto', 'Answer-Mode: Auto'),
    ('Call Info: Answer-After=0', 'Call Info: Answer-After=0'),
    ('Call-Info: Auto Answer', 'Call-Info: Auto Answer'),
    ('Call-Info: <sip:>;answer-after=0', 'Call-Info: <sip:>;answer-after=0'),
    ('P-Auto-Answer: normal', 'P-Auto-Answer: normal'),
]


class UserChannel(models.Model):
    _name = 'asterisk_plus.user_channel'
    _description = 'User Channel'

    #: Asterisk channel name. E.g. SIP/101.
    name = fields.Char(required=True)
    asterisk_user = fields.Many2one('asterisk_plus.user', required=True,
                                    ondelete='cascade')
    #: Server where the channel is defined.
    server = fields.Many2one(
        related='asterisk_user.server', readonly=True, store=True)
    #: Minion ID that is coming in system_name in events
    system_name = fields.Char(related='server.server_id', readonly=True)
    #: Odoo res.user who owns the channel.
    user = fields.Many2one(related='asterisk_user.user', readonly=True)
    #: When user has multiple channels and sequence calling is set this defines the call order.
    sequence = fields.Integer(default=100, index=True)
    #: Dial this channel when click to call is used.
    originate_enabled = fields.Boolean(default=True, string="Originate")
    #: O
    originate_context = fields.Char(
        default=lambda self: self._get_default_context(),
        string='Context')
    auto_answer_header = fields.Selection(AUTO_ANSWER_HEADERS)

    _sql_constraints = [
        ('server_channel_uniq', 'unique (server,name)',
         _('The channel is already defined for this server!')),
    ]

    def write(self, values):
        """
        """
        if not (self.env.user.has_group(
                'asterisk_plus.group_asterisk_admin') or
                self.env.user.id == SUPERUSER_ID):
            # User can only change some fields.
            restricted_fields = set(values.keys()) - set(USER_PERMITTED_FIELDS)
            if restricted_fields:
                raise ValidationError(
                    _('Fields {} not allowed to be changed by user!').format(
                        ', '.join(restricted_fields)))
        return super(UserChannel, self).write(values)

    @api.constrains('name')
    def _check_channel_name(self):
        """Validate channel name. It must contain / and must not contain spaces.
        """
        for rec in self:
            try:
                chan, name = rec.name.split('/')
            except ValueError:
                raise ValidationError(
                    _('Bad channel format. Example: SIP/101.'))
            if ' ' in rec.name:
                raise ValidationError()

    def _get_default_context(self):
        return self.env['asterisk_plus.settings'].sudo().get_param(
            'originate_context', 'odoo-from-internal')

    @api.model
    def get_user_channel(self, channel, system_name):
        """Take channel from an AMI event, parse it and return user channel object."""
        if '-' in channel:
            channel = '-'.join(channel.split('-')[:-1])
        user_channel = self.search([
            ('name', '=', channel),
            ('system_name', '=', system_name)], limit=1)
        return user_channel
