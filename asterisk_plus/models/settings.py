# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import inspect
import logging
import sys
from odoo import fields, models, api, release, _
from odoo.exceptions import ValidationError
from odoo.tools import ormcache

logger = logging.getLogger(__name__)

FORMAT_TYPE = 'e164'


def debug(rec, message):
    caller_module = inspect.stack()[1][3]
    if rec.env['asterisk_plus.settings'].sudo().get_param('debug_mode'):
        logger.info('++++++ {}: {}'.format(caller_module, message))


class Settings(models.Model):
    """One record model to keep all settings. The record is created on 
    get_param / set_param methods on 1-st call.
    """
    _name = 'asterisk_plus.settings'
    _description = 'Settings'

    #: Just a friends name for a settings form.
    name = fields.Char(compute='_get_name')
    #: Salt API URL, e.g. https://localhost:8000/
    saltapi_url = fields.Char(required=True, default='https://agent:48008',
                              string='Salt API URL')
    #: Salt API user.e.g. saltdev
    saltapi_user = fields.Char(required=True, string='Salt API User',
                               default='odoo')
    #: Salt API password .e.g. saltdev
    saltapi_passwd = fields.Char(required=True, string='Salt API Password',
                                 default='odoo')
    #: Debug mode
    debug_mode = fields.Boolean()
    #: Save all AMI messages on channels
    trace_ami = fields.Boolean(string='Trace AMI',
        help='Save all AMI messages on channels')
    permit_ip_addresses = fields.Char(
        string=_('Permit IP address(es)'),
        help=_('Comma separated list of IP addresses permitted to query caller'
               ' ID number, etc. Leave empty to allow all addresses.'))
    originate_context = fields.Char(
        string='Default context',
        default='from-internal', required=True,
        help='Default context to set when creating PBX / Odoo user mapping.')
    originate_timeout = fields.Integer(default=60, required=True)
    # Recording settings
    record_calls = fields.Boolean(
        default=True,
        help=_("If checked, call recording will be enabled"))
    recording_storage = fields.Selection(
        [('db', _('Database')), ('filestore', _('Files'))],
        default='filestore', required=True)
    delete_recordings = fields.Boolean(
        default=True,
        help='Keep recordings on Asterisk after upload to Odoo.')
    transcipt_recording = fields.Boolean(
        default=False, string=_("Transcript Recording"),
        help=_("If checked, call recordings will be transcripted using the Google Speech Recognition API."
               "Requires SpeechRecognition Python package installed to work."))
    google_sr_api_key = fields.Char(
        string=_("API Key"),
        help=_('The Google Speech Recognition API key.'
               'If not specified, it uses a generic key that works out of the box.'
               'This should generally be used for personal or testing purposes only, as it **may be revoked by Google at any time**.'))
    recognition_lang = fields.Char(
        default='en-US',
        string=_('Recognition Language'),
        help=_('RFC5646 language tag like ``"en-US"`` (US English) or ``"fr-FR"`` (International French)'))
    use_mp3_encoder = fields.Boolean(
        default=False, string=_("Encode to MP3"),
        help=_("If checked, call recordings will be encoded using MP3"
               "Requires lameenc Python package installed to work."))
    mp3_encoder_bitrate = fields.Selection(
        selection=[('16', '16kbps'),
                   ('32', '32kbps'),
                   ('48', '48kbps'),
                   ('64', '64kbps'),
                   ('96', '96kbps'),
                   ('128', '128 kbps')],
        required=False)
    mp3_encoder_quality = fields.Selection(
        selection=[('2', '2-Highest'),
                   ('3', '3'),
                   ('4', '4'),
                   ('5', '5'),
                   ('6', '6'),
                   ('7', '7-Fastest')],
        required=False)
    calls_keep_days = fields.Char(
        string=_('Call History Keep Days'),
        default='365',
        required=True,
        help=_('Calls older then set value will be removed.'))
    recordings_keep_days = fields.Char(
        string=_('Call Recording Keep Days'),
        default='365',
        required=True,
        help=_('Call recordings older then set value will be removed.'))
    auto_reload_calls = fields.Boolean(
        default=True,
        help=_('Automatically refresh active calls view'))
    auto_reload_channels = fields.Boolean(
        default=True,
        help=_('Automatically refresh active channels view'))
    auto_create_partners = fields.Boolean(
        default=False,
        help=_('Automatically create partner record on calls from uknown numbers.'))

    @api.model
    def _get_name(self):
        for rec in self:
            rec.name = 'General Settings'

    def open_settings_form(self):
        rec = self.env['asterisk_plus.settings'].search([])
        if not rec:
            rec = self.sudo().with_context(no_constrains=True).create({})
        else:
            rec = rec[0]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'asterisk_plus.settings',
            'res_id': rec.id,
            'name': 'General Settings',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }

    @api.model
    @ormcache('param')
    def get_param(self, param, default=False):
        """
        """
        data = self.search([])
        if not data:
            data = self.sudo().with_context(no_constrains=True).create({})
        else:
            data = data[0]
        return getattr(data, param, default)

    @api.model
    def set_param(self, param, value, keep_existing=False):
        """
        """
        data = self.search([])
        if not data:
            data = self.sudo().with_context(no_constrains=True).create({})
        else:
            data = data[0]
        # Check if the param is already there.
        if not keep_existing or not getattr(data, param):
            # TODO: How to handle Boolean fields!?
            setattr(data, param, value)
        else:
            debug(self, "Keeping existing value for param: {}".format(param))
        return True

    @api.model
    def create(self, vals):
        self.clear_caches()
        return super(Settings, self).create(vals)

    def write(self, vals):
        self.clear_caches()
        return super(Settings, self).write(vals)

    @api.constrains('record_calls')
    def record_calls_toggle(self):
        if 'no_constrains' in self.env.context:
            return
        # Enable/disable call recording event
        recording_event = self.env.ref('asterisk_plus.var_set_mixmon')
        # Check if enent can be updated
        if recording_event.update == 'no':
            raise ValidationError(
                _('Event {} is not updatebale'.format(recording_event.name)))
        recording_event.is_enabled = True if self.record_calls is True else False
        # Reload events map
        servers = self.env['asterisk_plus.server'].search([])
        for s in servers:
            s.ami_action(
                {'Action': 'ReloadEvents'},
            )

    @api.constrains('use_mp3_encoder')
    def _check_lameenc(self):
        """Checks if lameenc library is installed.
        """
        if 'no_constrains' in self.env.context:
            return
        try:
            import lameenc
        except ImportError:
            for rec in self:
                if rec.use_mp3_encoder:
                    raise ValidationError(
                        "Please install lameenc to enable MP3 encoding"
                        "(pip3 install lameenc).")

    @api.onchange('use_mp3_encoder')
    def on_change_mp3_encoder(self):
        if 'no_constrains' in self.env.context:
            return
        for rec in self:
            if rec.use_mp3_encoder:
                rec.mp3_encoder_bitrate = '96'
                rec.mp3_encoder_quality = '4'

    def sync_recording_storage(self):
        """Sync where call recordings are stored.
        """
        count = 0
        try:
            recordings = self.env['asterisk_plus.recording'].search([])
            for rec in recordings:
                if self.recording_storage == 'db' and not rec.recording_attachment:
                    rec.write({
                        'recording_data': False,
                        'recording_attachment': rec.recording_data})
                    count += 1
                    self.env.cr.commit()
                    logger.info('Recording {} moved to {}'.format(rec, self.recording_storage))
                elif self.recording_storage == 'filestore' and not rec.recording_data:
                    rec.write({
                        'recording_attachment': False,
                        'recording_data': rec.recording_attachment})
                    count += 1
                    self.env.cr.commit()
                    logger.info('Recording {} moved to {}'.format(rec, self.recording_storage))
        except Exception as e:
            logger.info('Sync recordings error: %s', str(e))
        finally:
            logger.info('Moved %s recordings', count)
            # Perform the garbage collection of the filestore.
            if release.version_info[0] >= 14:
                self.env['ir.attachment']._gc_file_store()
            else:
                self.env['ir.attachment']._file_gc()
