# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .server import get_default_server

logger = logging.getLogger(__name__)


class AccessList(models.Model):
    _name = 'asterisk_plus.access_list'
    _description = 'Access Lists of IP/Nets'
    _order = 'address'

    server = fields.Many2one('asterisk_plus.server', required=True,
                             ondelete='cascade', default=get_default_server)
    name = fields.Char(compute='_get_name')
    address = fields.Char(required=True, index=True)
    netmask = fields.Char()
    address_type = fields.Selection([('ip', 'IP Address'), ('net', 'Network')],
                                    required=True, default='ip')
    access_type = fields.Selection([('allow', 'Allow'), ('deny', 'Deny')],
                                   required=True, default='deny')
    # Comment is required because of ipset regex parsing on Agent.
    comment = fields.Char(required=True, default='No comment')
    is_enabled = fields.Boolean(default=True, string='Enabled')

    def _get_name(self):
        for rec in self:
            rec.name = rec.address if rec.address_type == 'ip' else \
                '{}/{}'.format(rec.address, rec.netmask)

    @api.model
    def create(self, vals):
        res = super(AccessList, self).create(vals)        
        if 'install_mode' in self.env.context:
            return res
        elif '_force_unlink' in self.env.context:
            return res
        self.update_rules()
        return res

    def write(self, vals):
        res = super(AccessList, self).write(vals)
        if 'install_mode' in self.env.context:
            return res
        elif '_force_unlink' in self.env.context:
            return res        
        self.update_rules()
        return res

    def unlink(self):
        res = super(AccessList, self).unlink()
        if 'install_mode' in self.env.context:
            return res
        elif '_force_unlink' in self.env.context:
            return res        
        self.update_rules()
        return res

    @api.model
    def update_rules(self, server_id=None):
        """Update access rules for server.
        """
        servers_domain = [] if not server_id else [('id', '=', server_id)]
        for server in self.env['asterisk_plus.server'].search(servers_domain):
            entries = self.search([('server', '=', server.id),
                                   ('is_enabled', '=', True)])
            rules = []
            for entry in entries:
                rules.append({
                    'address': entry.address,
                    'comment': entry.comment,
                    'netmask': entry.netmask,
                    'address_type': entry.address_type,
                    'access_type': entry.access_type})
            server.local_job(
                fun='asterisk.update_access_rules',
                arg=[rules],
                res_notify_uid=self.env.uid)


class Ban(models.Model):
    _name = 'asterisk_plus.access_ban'
    _description = 'Access Bans'
    _order = 'address'

    server = fields.Many2one('asterisk_plus.server', required=True,
                             ondelete='cascade')
    address = fields.Char(index=True, required=True)
    timeout = fields.Integer()
    packets = fields.Integer()
    bytes = fields.Integer()
    comment = fields.Char(index=True)

    @api.model
    def reload_bans(self, delay=0):
        """Get banned IPs from server.
        """
        for server in self.env['asterisk_plus.server'].search([]):
            server.local_job(
                fun='asterisk.get_banned',
                timeout=delay,
                res_model='asterisk_plus.access_ban',
                res_method='reload_bans_response',
                pass_back={
                    'notify_uid': self.env.uid,
                })

    @api.model
    def reload_bans_response(self, response, pass_back):
        """Creates record depending on response.
        """
        if not isinstance(response, list):
            logger.warning('RELOAD BANS ERROR: %s', response)
            return False
        # Get the server
        server = self.env.user.asterisk_server
        if not server:
            logger.warning('ASTERISK SERVER NOT FOUND FOR ACCOUNT %s',
                           self.env.user.name)
            return False
        # Remove current entries
        self.search(
            [('server', '=', server.id)]).with_context(
            unlink_bans_no_sync=True).unlink()
        # Update with the result
        for row in response:
            self.create({
                'server': server.id,
                'comment': row['comment'],
                'timeout': row['timeout'],
                'bytes': row['bytes'],
                'packets': row['packets'],
                'address': row['address'],
            })
        # Reload view
        server.reload_view(model='asterisk_plus.access_ban')
        return True

    def unlink(self):
        """Remove address from 'banned' ipset list.
        """
        if self.env.context.get('unlink_bans_no_sync'):
            return super(Ban, self).unlink()
        entries = {}
        # Populate entries with ip addresses
        for rec in self:
            entries.setdefault(rec.server, []).append(rec.address)
        res = super(Ban, self).unlink()
        # Now send to agent
        if res:
            for server in entries.keys():
                server.local_job(
                    fun='asterisk.remove_banned_addresses',
                    arg=[entries[server]],
                    res_notify_uid=self.env.uid)
        return res

    def add_to_whitelist(self):
        """Add address to whitelist or change access_type to allow if already exists.
        """
        self.ensure_one()
        # Check if address is not denied
        found = self.env['asterisk_plus.access_list'].search(
            [('address', '=', self.address)])
        if found:
            found.access_type = 'allow'
        # Not found, add a new one.
        else:
            self.env['asterisk_plus.access_list'].create({
                'server': self.server.id,
                'address': self.address,
                'address_type': 'ip',
                'access_type': 'allow',
            })
        # Reload bans after 1 second to allow update rules to complete
        self.unlink()
        self.reload_bans(delay=1)
