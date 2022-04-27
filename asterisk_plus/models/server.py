# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
# -*- coding: utf-8 -*-
import base64
from datetime import datetime
import json
import logging
import time
import urllib
import uuid
import yaml
from odoo import api, models, fields, SUPERUSER_ID, registry, release, _
from odoo.exceptions import ValidationError
try:
    import humanize
    HUMANIZE = False
except ImportError:
    HUMANIZE = False
import pepper
from .settings import debug, FORMAT_TYPE
from .res_partner import strip_number

logger = logging.getLogger(__name__)


#: Click-to-call originate number format.
ORIGINATE_FORMAT_TYPES = [
    ('e164', _('E.164 Format')),
    ('out_of_country', _('Out of Country Format')),
    ('no_format', _('No Formatting')),
]


def get_default_server(rec):
    try:
        return rec.env.ref('asterisk_plus.default_server')
    except Exception:
        logger.exception('Cannot get default server!')
        return False


class Server(models.Model):
    _name = 'asterisk_plus.server'
    _description = "Asterisk Server"

    #: Server's name for humans.
    name = fields.Char(required=True)
    #: Server's minion ID.
    server_id = fields.Char(string="Minion ID", required=True)

    user = fields.Many2one('res.users', ondelete='restrict', required=True, readonly=True)
    tz = fields.Selection(related='user.tz', readonly=False)
    country_id = fields.Many2one(related='user.country_id', readonly=False)
    password = fields.Char(related='user.password', string="Password", readonly=False)
    custom_command = fields.Char()
    custom_command_reply = fields.Text()
    conf_count = fields.Integer(compute='_conf_count')
    conf_files = fields.One2many(comodel_name='asterisk_plus.conf',
                                 inverse_name='server')
    init_conf_sync = fields.Boolean(
        string='Initial Update Done',
        help='Uncheck to receive files from Asterisk on next boot.')
    conf_sync = fields.Boolean(
        string='Update .conf files',
        default=True,
        help='Send files to / from Asterisk on Asterisk / Agent start',
    )
    conf_sync_direction = fields.Selection(selection=[
        ('asterisk_to_odoo', 'Asterisk -> Odoo'),
        ('odoo_to_asterisk', 'Odoo -> Asterisk')],
        string='Update Direction',
        default='odoo_to_asterisk',
        help='Where to send .conf files on every Agent / Asterisk start.'
    )
    sync_date = fields.Datetime(readonly=True)
    sync_uid = fields.Many2one('res.users', readonly=True, string='Sync by')
    cli_area = fields.Char(string="Console", compute='_get_cli_area')
    console_url = fields.Char(default='wss://agent:30000/')
    console_auth_token = fields.Char()

    _sql_constraints = [
        ('user_unique', 'UNIQUE("user")', 'This user is already used for another server!'),
    ]

    def open_server_form(self):
        rec = self.env.ref('asterisk_plus.default_server')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'asterisk_plus.server',
            'res_id': rec.id,
            'name': 'Agent',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }

    @api.model
    def set_minion_data(self, minion_id, timezone):
        """Called by minion to set server's ID on login."""
        server = self.search([('user', '=', self.env.uid)])
        server.server_id = minion_id
        logger.info('Minion %s has been connected.', minion_id)
        try:
            server.tz = timezone
        except Exception as e:
            # It's not a critical error just inform.
            logger.warning('Could not set server timezone to %s: %s', timezone, e)
        return True

    @api.model
    def _get_saltapi(self, force_login=False):
        """Get Salt API pepper instance.
        TODO: Cache auth in ORM cache not ir.config_parameter.
        Returns:
            A connected pepper instance. See `libpepper.py <https://github.com/saltstack/pepper/blob/develop/pepper/libpepper.py>`__ for details.
        """
        get_param = self.env['asterisk_plus.settings'].sudo().get_param
        saltapi = pepper.Pepper(get_param('saltapi_url'))
        # Get saltapi auth params
        auth = self.env[
            'ir.config_parameter'].sudo().get_param('saltapi_auth')
        # Check if we already logged in.
        if not force_login and auth:
            # Convert into dictionary.
            try:
                auth = json.loads(auth)
            except json.decoder.JSONDecodeError as e:
                logger.error('Auth token error: %s: %s', auth, e)
                auth = {'expire': 0}
            if auth['expire'] - time.time() < 0:
                # Token is no longer valid so need to login.
                logger.info('SALT API LOGIN AS TOKEN IS EXPIRED.')
                saltapi.login(
                    get_param('saltapi_user'),
                    get_param('saltapi_passwd'),
                    'file',
                )
                # Update auth data.
                self.env['ir.config_parameter'].sudo().set_param(
                    'saltapi_auth', json.dumps(saltapi.auth))
            else:
                # Token not expired, take it.
                saltapi.auth = auth
        else:
            # Token is no longer valid so need to login.
            logger.info('SALT API LOGIN.')
            saltapi.login(
                get_param('saltapi_user'),
                get_param('saltapi_passwd'),
                'file',
            )
            self.env['ir.config_parameter'].set_param(
                'saltapi_auth', json.dumps(saltapi.auth))
        return saltapi

    def local_job(self, fun, arg=None, kwarg=None, timeout=None,
                  res_model=None, res_method=None, res_notify_uid=None,
                  pass_back=None, sync=False):
        """Execute a function on Salt minion.

        Args:
            fun (str): function name. Example: test.ping.
            arg (list): positional arguments.
            kwarg (dict): named arguments.
            timeout (int): function execution timeout in seconds.
            res_model (str): name of the model to receive function result.
            res_method (str): name of the method to receive function result. Function result is passed as the 1-st paramater.
            res_notify_uid (int): User ID that will receive function result in notification message.
            pass_back (dict): json serializable dictionary that is passed to res_method as the 2-nd paramater.
        """
        try:
            saltapi = self.sudo()._get_saltapi()
        except urllib.error.URLError:
            raise ValidationError('Cannot connect to Salt API process.')
        # Wrap calling function to be able to re-login on session expiration.

        def call_fun():
            if not sync:
                ret = saltapi.local_async(tgt=self.server_id, fun=fun, arg=arg,
                                          kwarg=kwarg, timeout=timeout, ret='odoo')
                self.env['asterisk_plus.salt_job'].sudo().create({
                    'jid': ret['return'][0]['jid'],
                    'res_model': res_model,
                    'res_method': res_method,
                    'res_notify_uid': res_notify_uid,
                    'pass_back': json.dumps(pass_back) if pass_back else False,
                })
            else:
                ret = saltapi.local(tgt=self.server_id, fun=fun, arg=arg,
                                    kwarg=kwarg, timeout=timeout)
            # TODO: Add server:
            # {'return': [{'jid': '20210928122846179815', 'minions': ['asterisk']}]}
            # TODO: When minion is not accepted it raises error.
            debug(self, json.dumps(ret, indent=2))
            if not self.env.context.get('no_commit'):
                # Commit ASAP so that returner can find the job.
                # TODO: Move the above to separate transation not to commit the current one.
                self.env.cr.commit()
            return ret
        try:
            return call_fun()
        except ConnectionResetError:
            raise ValidationError('Salt API connection reset! Check HTTP/HTTPS settings.')
        except urllib.error.URLError:
            raise ValidationError('Salt API connection error!')
        #except pepper.ServerError ?? TODO: catch when master is done.
        #    raise ValidationError('Salt Master connection error!')
        except KeyError as e:
            if 'jid' in str(e):
                raise ValidationError('No job ID was returned. Check Minion ID!')
            else:
                logger.exception('Key Error:')
        except pepper.exceptions.PepperException as e:
            if 'Authentication denied' in str(e):
                logger.warning('Salt Authentication denied.')
                saltapi = self.sudo()._get_saltapi(force_login=True)
                return call_fun()
            else:
                raise

    def ami_action(self, action, timeout=5, no_wait=False, as_list=None, **kwargs):
        """Send AMI action to the server.

        Args:
            action (dict): A dictionary with action.

        Returns:
            A list of results as received from Asterisk.

        Example action:

        .. code:: python

            {'Action': 'Ping'}

        Result:

        .. code:: python

            [{'Response': 'Success', 'ActionID': 'action/67cfd99b-8138-4cb5-9473-4e8be6d1cbe9/1/5026', 'Ping': 'Pong', 'Timestamp': '1631707333.341870', 'content': ''}]        

        """
        return self.local_job(
            fun='asterisk.manager_action',
            arg=action,
            kwarg={
                'timeout': timeout,
                'no_wait': no_wait,
                'as_list': as_list
            }, **kwargs)

    ##################### UI BUTTONS ==========================================

    def ping(self):
        """Called from server form to test the connectivity.

        Returns:
            True or False if Salt minion is not connected.
        """
        self.local_job(fun='test.ping',
                      res_model='asterisk_plus.server',
                      res_method='ping_reply',
                      pass_back={'uid': self.env.user.id})

    @api.model
    def ping_reply(self, data, pass_back):
        self.env.user.asterisk_plus_notify(str(data), uid=pass_back['uid'])


    def asterisk_ping(self):
        """Called from server form to test AMI connectivity.
        """
        self.ami_action({'Action': 'Ping'}, res_notify_uid=self.env.uid)

    @api.model
    def on_fully_booted(self, event):
        """AMI FullyBooted event.
        Raised when all Asterisk initialization procedures have finished.
        """
        logger.info(
            'System {} FullyBooted, uptime: {}, Last reload: {}.'.format(
                event.get('SystemName'), event.get('Uptime'),
                event.get('LastReload')))
        server = self.env.user.asterisk_server
        return server.sync_configs()

    def set_callerid(self, number, model=None, res_id=None):
        """Sets callerid.

        Args:
            number (str): Caller number.
            model (str): Odoo model, comes from click2call.
            res_id (int): Odoo res_id, comes from click2call.
        Returns:
            Callers ID ('John <1001>').
        """
        if model and res_id:
            obj = self.env[model].browse(res_id)
            if hasattr(obj, 'name'):
                name = obj.name
            else:
                name = number
            return 'To: {} <{}>'.format(name, number)
        else:
            return 'To: {} <{}>'.format(number, number)

    def format_number(self, number, model=None, res_id=None):
        if model and res_id:
            debug(self, 'FORMAT NUMBER FOR MODEL {}'.format(model))
            obj = self.env[model].browse(res_id)
            if getattr(obj, '_format_number', False):
                number = obj._format_number(number, format_type=FORMAT_TYPE)
                debug(self, 'MODEL FORMATTED NUMBER: {}'.format(number))
                return number
        return strip_number(number)

    @api.model
    def originate_call(self, number, model=None, res_id=None, user=None, dtmf_variables=None):
        """Originate Call with click2dial widget.

          Args:
            number (str): Number to dial.
        """
        if not user:
            user = self.env.user
        if not user.asterisk_users:
            raise ValidationError('PBX User is not defined!') # sdd sd sd sd sdsd sdsd s
        # Format number
        number = self.format_number(number, model, res_id)
        # Set CallerID
        callerid = self.set_callerid(number, model, res_id)
        # Get originate timeout
        originate_timeout = float(self.env[
            'asterisk_plus.settings'].sudo().get_param('originate_timeout'))

        for asterisk_user in self.env.user.asterisk_users:
            if not asterisk_user.channels:
                raise ValidationError('SIP channels not defined for user!')
            originate_channels = [k for k in asterisk_user.channels if k.originate_enabled]
            if not originate_channels:
                raise ValidationError('No channels with originate enabled!')
            variables = asterisk_user._get_originate_vars()
            # Save original callerid
            variables.append('OUTBOUND_CALLERID="{}" <{}>'.format(
                self.env.user.name, self.env.user.asterisk_users.exten))
            for ch in originate_channels:
                channel_vars = variables.copy()
                if ch.auto_answer_header:
                    header = ch.auto_answer_header
                    try:
                        pos = header.find(':')
                        param = header[:pos]
                        val = header[pos+1:]
                        if 'PJSIP' in ch.name.upper():
                            channel_vars.append(
                                'PJSIP_HEADER(add,{})={}'.format(
                                    param.lstrip(), val.lstrip()))
                        else:
                            channel_vars.append(
                                'SIPADDHEADER={}: {}'.format(
                                    param.lstrip(), val.lstrip()))
                    except Exception:
                        logger.warning(
                            'Cannot parse auto answer header: %s', header)

                if dtmf_variables:
                    channel_vars.extend(dtmf_variables)

                channel_id = uuid.uuid4().hex
                other_channel_id = uuid.uuid4().hex
                # Create a call.
                call_data = {
                    'server': asterisk_user.server.id,
                    'uniqueid': channel_id,
                    'calling_user': self.env.user.id,
                    'calling_number': asterisk_user.exten,
                    'called_number': number,
                    'started': datetime.now(),
                    'direction': 'out',
                    'is_active': True,
                    'status': 'progress',
                    'model': model,
                    'res_id': res_id,
                }
                if model == 'res.partner':
                    # Set call partner
                    call_data['partner'] = res_id
                call = self.env['asterisk_plus.call'].create(call_data)
                self.env['asterisk_plus.channel'].create({
                        'server': asterisk_user.server.id,
                        'user': self.env.user.id,
                        'call': call.id,
                        'channel': ch.name,
                        'uniqueid': channel_id,
                        'linkedid': other_channel_id,
                })
                if not self.env.context.get('no_commit'):
                    self.env.cr.commit()
                action = {
                    'Action': 'Originate',
                    'Context': ch.originate_context,
                    'Priority': '1',
                    'Timeout': 1000 * originate_timeout,
                    'Channel': ch.name,
                    'Exten': number,
                    'Async': 'true',
                    'EarlyMedia': 'true',
                    'CallerID': callerid,
                    'ChannelId': channel_id,
                    'OtherChannelId': other_channel_id,
                    'Variable': channel_vars,
                },

                ch.server.ami_action(action, res_model='asterisk_plus.server',
                                     res_method='originate_call_response',
                                     pass_back={'uid': self.env.user.id})

    @api.model
    def originate_call_response(self, data, pass_back):
        debug(self, json.dumps(data, indent=2))
        if data[0]['Response'] == 'Error':
            self.env.user.asterisk_plus_notify(
                data[0]['Message'], uid=pass_back['uid'], warning=True)

    @api.onchange('custom_command')
    def send_custom_command(self):
        try:
            cmd_line = self.custom_command.split(' ')
            cmd, params_list = cmd_line[0], cmd_line[1:]
            kwarg = {}
            for param_val in params_list:
                param, val = param_val.split('=')
                kwarg[param] = val
            res = self.local_job(fun=cmd, kwarg=kwarg, sync=True)
            ret = res['return'][0][self.server_id]
            if isinstance(ret, str):
                pass
            else:
                ret = yaml.dump(ret, default_flow_style=False)
            self.custom_command_reply = ret
        except ValueError:
            raise ValidationError('Command not understood! Example: network.ping host=google.com')

    ##################### Work with configs ==========================================

    def _conf_count(self):
        for rec in self:
            rec.conf_count = self.env['asterisk_plus.conf'].search_count(
                [('server', '=', rec.id)])

    def apply_changes(self, raise_exc=False):
        """Apply changes with conf files.
        """
        self.ensure_one()
        changed_configs = self.env['asterisk_plus.conf'].search(
            [('server', '=', self.id), ('is_updated', '=', True)])
        try:
            for conf in changed_configs:
                conf.upload_conf()
            if changed_configs:
                self.reload_action(delay=0.5)
                return True
            else:
                self.env['res.users'].asterisk_plus_notify(
                    _('System {} no changes detected.').format(self.name))
                return False
        except Exception as e:
            if raise_exc:
                raise
            else:
                raise ValidationError('Apply error: {}'.format(e))

    @api.model
    def apply_all_changes(self):
        for server in self.search([]):
            server.apply_changes()
        return True

    def download_all_conf(self):
        """Download all config files from server.
        """
        try:
            self.ensure_one()
        except ValueError as e:
            if 'Expected singleton: asterisk_plus.server()' in str(e):
                raise Exception(
                    'Odoo account %s is not set to Remote Agent.', self.env.uid)
        self.local_job(
            fun='asterisk.get_all_configs',
            res_model='asterisk_plus.server',
            res_method='download_all_conf_response',
            pass_back={
                'notify_uid': self.env.user.id,
            })

    @api.model
    def download_all_conf_response(self, response, pass_back):
        if not isinstance(response, dict):
            return False

        server = self.env.user.asterisk_server
        for file, data in response.items():
            conf = self.env[
                'asterisk_plus.conf'].with_context(
                conf_no_update=True).get_or_create(server.id, file)
            conf.write({
                'content': base64.b64decode(data['file_data'].encode()),
                'sync_date': fields.Datetime.now(),
                'sync_uid': self.env.uid,
                'is_updated': False,
            })
        # Update last sync
        server.write({'sync_date': fields.Datetime.now(),
                      'init_conf_sync': True,
                      'sync_uid': self.env.uid})
        uid = pass_back.get('notify_uid')
        if uid:
            self.env['res.users'].asterisk_plus_notify(
                _('Config files download complete.'), uid=uid)
        return True

    def upload_all_conf(self, auto_reload=False):
        """Upload all config files on server.
        """
        self.ensure_one()
        data = {}
        for rec in [k for k in self.conf_files if k.content]:
            data[rec.name] = base64.b64encode(rec.content.encode()).decode()
        self.local_job(
            fun='asterisk.put_all_configs',
            arg=[data],
            res_model='asterisk_plus.server',
            res_method='upload_all_conf_response',
            pass_back={
                'notify_uid': self.env.user.id,
                'auto_reload': True
            })
        self.conf_files.write({'is_updated': False})
        self.write({'sync_date': fields.Datetime.now(),
                    'sync_uid': self.env.uid})

    @api.model
    def upload_all_conf_response(self, response, pass_back):
        if not isinstance(response, bool):
            return False
        uid = pass_back.get('notify_uid')
        if uid:
            self.env['res.users'].asterisk_plus_notify(
                _('Config files upload complete.'), uid=uid)
        if pass_back['auto_reload']:
            self.env.user.asterisk_server.reload_action()
        return True

    def sync_configs(self):
        """Sync configs between Odoo and Asterisk.
        """
        self.ensure_one()
        server = self
        if not server.conf_sync:
            logger.info('Not syncing Asterisk config files, not enabled.')
            return True
        if server.conf_sync_direction == 'odoo_to_asterisk':
            # Check if there was a first config upload
            if not server.init_conf_sync:
                logger.info('Getting all .conf files from %s for the 1-st time...',
                            server.name)
                server.download_all_conf()
            else:
                logger.info('Sending .conf files to Asterisk system %s...',
                            server.name)
                server.upload_all_conf()
                server.reload_action(delay=3)
        else:
            # Get configs from Asterisk
            logger.info('Getting all .conf files from Asterisk system %s...',
                        server.name)
            server.download_all_conf()
        return True

    def reload_action(self, module=None, notify_uid=None, delay=0):
        """Send 'Reload' action to Asterisk.
        """
        self.ensure_one()
        action = {'Action': 'Reload'}
        if module:
            action['Module'] = module
        self.ami_action(
            action,
            timeout=delay,
            res_notify_uid=notify_uid or self.env.uid)

    def restart_action(self, notify_uid=None, delay=0):
        """Send 'core restart now' command to Asterisk.
        """
        self.ensure_one()
        action = {
            'Action': 'Command',
            'Command': 'core restart now'
        }
        self.ami_action(
            action,
            timeout=delay,
            res_notify_uid=notify_uid or self.env.uid)

    ##################### Console ==========================================

    def _get_cli_area(self):
        for rec in self:
            rec.cli_area = '/asterisk_plus/console/{}'.format(rec.id)

    def open_console_button(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/asterisk_plus/console/{}".format(self.id),
            "target": "new",
        }

    @api.model
    def reload_view(self, model=None):
        """Reloads view. Sends 'reload_view' action to actions.js
        """
        self.env['bus.bus'].sendone(
            'asterisk_plus_actions',
            {'action': 'reload_view', 'model': model})
        return True
