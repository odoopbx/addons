# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import base64
import logging
import json
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
from .server import get_default_server

logger = logging.getLogger(__name__)


class AsteriskConf(models.Model):
    _name = 'asterisk_plus.conf'
    _description = 'Configuration Files'
    _rec_name = 'name'
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True, copy=False)
    server = fields.Many2one(comodel_name='asterisk_plus.server',
                             default=get_default_server,
                             required=True, ondelete='cascade')
    content = fields.Text()
    is_updated = fields.Boolean(string=_('Updated'))
    sync_date = fields.Datetime(readonly=True)
    sync_uid = fields.Many2one('res.users', readonly=True, string='Sync by')
    version = fields.Integer(
        default=1, required=True, index=True, readonly=True)

    @api.model
    def create(self, vals):
        if not self.env.context.get('conf_no_update'):
            vals['is_updated'] = True
        rec = super(AsteriskConf, self).create(vals)
        return rec

    @api.constrains('name', 'active')
    def check_name(self):
        for rec in self:
            existing = self.env[
                'asterisk_plus.conf'].search(
                [('name', '=', rec.name), ('server', '=', rec.server.id)])
            if len(existing) > 1:
                raise ValidationError(
                    'This filename is already used!')

    def write(self, vals):
        if 'name' in vals:
            raise ValidationError(
                _('Rename not possible. Create a new file and copy & paste.'))
        no_update = vals.get(
            'content') and self.env.context.get('conf_no_update')
        if 'content' in vals and not no_update:
            vals['is_updated'] = True
        if 'content' in vals and 'version' not in vals and not no_update:
            # Inc version
            for rec in self:
                vals['version'] = rec.version + 1
                super(AsteriskConf, rec).write(vals)
        else:
            super(AsteriskConf, self).write(vals)
        return True

    def unlink(self):
        for rec in self:
            if not rec.active:
                super(AsteriskConf, rec).unlink()
            else:
                rec.active = False
                self.unlink_on_asterisk()
        return True

    def unlink_on_asterisk(self):
        """Delete conf file on server.
        """
        names = self.mapped('name')
        servers = self.mapped('server')
        for server in servers:
            server.local_job(
                fun='asterisk.delete_config',
                arg=[names],
                res_notify_uid=self.env.uid)

    def refresh_button(self):
        return True

    def toggle_active(self):
        for rec in self:
            rec.write({
                'active': not rec.active,
                'is_updated': not rec.active,
            })

    @api.model
    def get_or_create(self, server_id, name, content=''):
        """Get existing conf or create a new one.
        """
        conf = self.env['asterisk_plus.conf'].search(
            [('server', '=', server_id), ('name', '=', name)])
        if not conf:
            data = {'server': server_id, 'name': name, 'content': content}
            conf = self.env['asterisk_plus.conf'].create(data)
        return conf

    def include_from(self, from_name):
        self.ensure_one()
        from_conf = self.env['asterisk_plus.conf'].search(
            [('name', '=', from_name), ('server', '=', self.server.id)])
        if not from_conf or not from_conf.content:
            logger.warning(
                'File %s not found or empty, ignoring #tryinclude.', from_name)
            return
        # Check if include is already there.
        conf_basename = from_name.split('.')[0]
        include_string = '#tryinclude {}_odoo*.conf'.format(conf_basename)
        if (include_string not in from_conf.content):
            from_conf.content += '\n{}\n'.format(include_string)

    def upload_conf(self):
        """Upload conf on server.
        """
        self.ensure_one()
        self.server.local_job(
            fun='asterisk.put_config',
            arg=[self.name, "'{}'".format(base64.b64encode(self.content.encode()).decode())],
            res_model='asterisk_plus.conf',
            res_method='upload_conf_response',
            pass_back={
                'res_id': self.id,
                'uid': self.env.uid,
                'name': self.name,
            })

    @api.model
    def upload_conf_response(self, response, pass_back):
        if not isinstance(response, bool):
            logger.warning('Upload conf error: %s', response)
            self.env.user.asterisk_plus_notify(
                'File {} error: {}'.format(
                    pass_back['name'],
                    response),
                    uid=pass_back['uid'])
            return False
        conf = self.browse(pass_back['res_id'])
        conf.write({
            'is_updated': False,
            'sync_date': fields.Datetime.now(),
            'sync_uid': pass_back['uid']
        })
        self.env.user.asterisk_plus_notify(
            'File {} uploaded.'.format(pass_back['name']),
            uid=pass_back['uid'])
        return True

    def download_conf(self, notify_uid=None):
        """Download conf from server.
        """
        self.ensure_one()
        self.server.local_job(
            fun='asterisk.get_config',
            arg=[self.name],
            res_model='asterisk_plus.conf',
            res_method='download_conf_response',
            pass_back={
                'res_id': self.id,
                'uid': self.env.uid,
                'name': self.name,
            })

    @api.model
    def download_conf_response(self, response, pass_back):
        if not isinstance(response, dict):
            logger.warning('Download conf error: %s', response)
            self.env.user.asterisk_plus_notify(
                'File {} error: {}'.format(
                    pass_back['name'],
                    response),
                    uid=pass_back['uid'])
            return False
        conf = self.browse(pass_back['res_id'])
        conf.with_context({'conf_no_update': True}).write({
            'content': base64.b64decode(
                response['file_data'].encode()).decode('latin-1'),
            'sync_date': fields.Datetime.now(),
            'sync_uid': self.env.user.id,
            'is_updated': False,
        })
        self.env.user.asterisk_plus_notify(
            'File {} downloaded.'.format(
                pass_back['name']),
                uid=pass_back['uid'])
        # Reload file form
        if tools.odoo.release.version_info[0] < 15:
            msg = {
                'action': 'reload_view',
                'model': 'asterisk_plus.conf'
            }
            self.env['bus.bus'].sendone('asterisk_plus_actions', json.dumps(msg))
        else:
            msg = {'model': 'asterisk_plus.conf'}
            self.env['bus.bus']._sendone(
                'asterisk_plus_actions',
                'reload_view',
                json.dumps(msg)
            )
        return True
