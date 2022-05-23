import logging
from odoo import models, fields, api, tools, release, _
from odoo.exceptions import ValidationError, UserError
from .server import get_default_server

logger = logging.getLogger(__name__)


class ResUser(models.Model):
    _inherit = 'res.users'

    asterisk_users = fields.One2many(
        'asterisk_plus.user', inverse_name='user')
    # Server of Agent account, One2one simulation.
    asterisk_server = fields.Many2one('asterisk_plus.server', compute='_get_asterisk_server')

    def _get_asterisk_server(self):
        for rec in self:
            # There is an unique constraint to limit 1 user per server.
            rec.asterisk_server = self.env['asterisk_plus.server'].search(
                [('user', '=', self.env.uid)], limit=1)

    @api.model
    def asterisk_plus_notify(self, message, title='PBX', uid=None,
                             sticky=False, warning=False):
        """Send a notification to logged in Odoo user.

        Args:
            message (str): Notification message.
            title (str): Notification title. If not specified: PBX.
            uid (int): Odoo user UID to send notification to. If not specified: calling user UID.
            sticky (boolean): Make a notiication message sticky (shown until closed). Default: False.
            warning (boolean): Make a warning notification type. Default: False.
        Returns:
            Always True.
        """
        # Use calling user UID if not specified.
        if not uid:
            uid = self.env.uid

        if tools.odoo.release.version_info[0] < 15:
            self.env['bus.bus'].sendone(
                'asterisk_plus_actions_{}'.format(uid),
                {
                    'action': 'notify',
                    'message': message,
                    'title': title,
                    'sticky': sticky,
                    'warning': warning
                })
        else:
            self.env['bus.bus']._sendone(
                'asterisk_plus_actions_{}'.format(uid),
                'asterisk_plus_notify',
                {
                    'message': message,
                    'title': title,
                    'sticky': sticky,
                    'warning': warning
                })

        return True

    def get_pbx_user_settings(self):
        """Used from actions.js to get user settings.
        """
        self.ensure_one()
        res = {}
        for ast_user in self.asterisk_users:
            res[ast_user.server_id] = {}
            user_channels = self.env['asterisk_plus.user_channel'].search(
                [('asterisk_user', '=', ast_user.id)])        
            for user_channel in user_channels:
                # Set channels.
                res[ast_user.server_id].setdefault(
                    'channels', []).append(user_channel.name)
            # Set open_reference.
            res[ast_user.server_id]['open_reference'] = ast_user.open_reference
        return res
